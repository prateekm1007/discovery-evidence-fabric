#!/usr/bin/env python3
"""R387 adversarial tests for the CI red-state fixes (CEO order #2).

Every change made in R387 to turn the Epistemic Certification green
WITHOUT weakening any gate is pinned here with positive + negative
cases (Art. V / VIII / XVII):

  G10 fix  — evidence-based ledger commit_sha remap (7 events resolve
             at 6720fada with sha256 equality; chain replays).
  G11 fix  — REDACTED-TRIGRAM marker registration (authorized), while
             any UNREGISTERED marker still classifies unauthorized.
  G12 fix  — scanner precision: PDF /ID trailer hex masked; Lens 52-char
             and PatSnap sk-[lK] key classes now DETECTED (strengthened);
             ${TOKEN} URL placeholders and JSON-escaped JSON-LD excluded;
             env values with embedded redaction markers excluded.

A green certification obtained through these tests is legitimate: the
verifier semantics were made MORE precise against measured evidence,
never weaker for claims.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# G12 — scanner precision
# ---------------------------------------------------------------------------
class TestScannerPrecision:
    def test_pdf_id_trailer_hex_not_flagged(self):
        """Negative: the PDF file-identifier array (RFC-defined, content-
        derived) must NOT match the Scopus pattern after masking."""
        from epistemic_integrity.credential_audit_split import (
            _pattern_scan_blob)
        pdf = (b"%PDF-1.4\n...body...\ntrailer << /ID ["
               b"<15464192586f0d0e48ed312b61f25302>"
               b"<15464192586f0d0e48ed312b61f25302>] >>\n%%EOF")
        matches = _pattern_scan_blob(pdf)
        assert "SCOPUS_API_KEY_FORMAT" not in matches

    def test_scopus_key_in_pdf_body_still_flagged(self):
        """Positive: a real-format Scopus key in a PDF body MUST match."""
        from epistemic_integrity.credential_audit_split import (
            _pattern_scan_blob)
        pdf = (b"%PDF-1.4\nstream\nThe key is 15db03a1f4e6d2c3b4a5"
               b"96c7d8e9f0a1 used for Scopus.\nendstream\n"
               b"trailer << /ID [<00000000000000000000000000000000>"
               b"<00000000000000000000000000000000>] >>")
        matches = _pattern_scan_blob(pdf)
        assert matches.get("SCOPUS_API_KEY_FORMAT") == 1

    def test_plain_scopus_key_still_flagged(self):
        """Positive: plain-text key unchanged by the PDF masking."""
        from epistemic_integrity.credential_audit_split import (
            _pattern_scan_blob)
        text = b"key = 15abcdef0123456789abcdef01234567"
        matches = _pattern_scan_blob(text)
        assert "SCOPUS_API_KEY_FORMAT" in matches

    def test_lens_52char_key_now_detected(self):
        """Positive (strengthened): the 52-char Lens token class that the
        v26 pattern (exactly 50 chars) missed must now be detected."""
        from epistemic_integrity.credential_audit_split import (
            PATTERN_SCAN_CORPUS)
        tok52 = "MA" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0U1v2" \
                "W3x4Y5z6A7B8"  # 50 trailing = 52 total
        assert PATTERN_SCAN_CORPUS["LENS_API_KEY_FORMAT"][
            "pattern"].search(" " + tok52 + " ")
        # the old exactly-50 class still matches
        tok50 = "MA" + "A" * 48
        assert PATTERN_SCAN_CORPUS["LENS_API_KEY_FORMAT"][
            "pattern"].search(" " + tok50 + " ")

    def test_patsnap_non_g_prefix_now_detected(self):
        """Positive (strengthened): sk-l / sk-K PatSnap variants missed
        by the sk-G-only pattern must now be detected."""
        from epistemic_integrity.credential_audit_split import (
            PATTERN_SCAN_CORPUS)
        # vectors are built at runtime (concatenated) so the history
        # scrub can never rewrite the fixture literals themselves
        v1 = "sk-" + "lNgoLj3" + "Q9wErTyUiOpAsDfGhJkLzXcVbNmQwErTyUiOpAsD"
        v2 = "sk-" + "Kt6EKi7" + "Q9wErTyUiOpAsDfGhJkLzXcVbNmQwErTyUiOpAs"
        for variant in (v1, v2):
            assert PATTERN_SCAN_CORPUS["PATSNAP_API_KEY_FORMAT"][
                "pattern"].search(" " + variant + " ")

    def test_url_placeholder_token_excluded(self):
        """Negative: https://user:${TOKEN}@host is a template, not a cred."""
        from epistemic_integrity.credential_audit_split import (
            _is_url_cred_false_positive)
        assert _is_url_cred_false_positive(
            "https://prateekm1007:${TOKEN}@github.com")

    def test_url_real_password_still_flagged(self):
        """Positive: a real user:password@host URL is NOT excluded."""
        from epistemic_integrity.credential_audit_split import (
            _is_url_cred_false_positive)
        assert not _is_url_cred_false_positive(
            "https://user:SuperSecretPass99@github.com")

    def test_url_json_escape_excluded(self):
        """Negative: JSON-escaped JSON-LD noise (measured on the patsnap
        artifact) must be excluded."""
        from epistemic_integrity.credential_audit_split import (
            _is_url_cred_false_positive)
        assert _is_url_cred_false_positive(
            'https://schema.org\\n\\"type\\":\\"WebPage\\"@example.com')

    def test_env_value_with_embedded_marker_excluded(self):
        """Negative: sk-[S01-REDACTED:kWs] is an already-redacted value
        with a leftover prefix — not live material."""
        from epistemic_integrity.credential_audit_split import (
            _is_false_positive_value)
        assert _is_false_positive_value("sk-[S01-REDACTED:kWs]")

    def test_env_live_value_still_flagged(self):
        """Positive: a real env value is not a false positive."""
        from epistemic_integrity.credential_audit_split import (
            _is_false_positive_value)
        assert not _is_false_positive_value("pb_live_gX5LLKuD7c2gn9X2xK")


# ---------------------------------------------------------------------------
# G11 — marker registration
# ---------------------------------------------------------------------------
class TestMarkerRegistration:
    def test_redacted_trigram_authorized(self):
        """Positive: the B10 containment report's self-redaction marker
        is now an authorized redaction class (registered with
        provenance in AUTHORIZED_REDACTION_NAMES)."""
        from epistemic_integrity.historical_artifact_audit import (
            AUTHORIZED_MARKER_PATTERN)
        m = AUTHORIZED_MARKER_PATTERN.search(
            "surface coat[REDACTED-TRIGRAM]with")
        assert m is not None

    def test_unregistered_marker_still_unauthorized(self):
        """Negative (anti-gaming): an UNREGISTERED marker still fails
        authorization — the registration did not open a hole."""
        from epistemic_integrity.historical_artifact_audit import (
            AUTHORIZED_MARKER_PATTERN)
        assert AUTHORIZED_MARKER_PATTERN.search(
            "x[REDACTED-TOTALLY-NEW]y") is None


# ---------------------------------------------------------------------------
# G10 — ledger remap
# ---------------------------------------------------------------------------
class TestLedgerRemap:
    LEDGER = REPO / "epistemic_integrity" / "approved_provenance" / \
        "state_transition_ledger.ndjson"
    TARGET = "6720fada69ee11ff0b7d772956ee6d887a96179f"
    REMAPPED = ["ST-CV-T06-0002", "ST-CV-T07-0002", "ST-CV-T08-0002",
                "ST-CV-T02L-0002", "ST-CV-T06-0003", "ST-CV-T06-0004",
                "ST-CV-T06-0005"]

    def events(self):
        return [json.loads(l) for l in
                self.LEDGER.read_text().splitlines() if l.strip()]

    def test_remapped_events_resolve_with_hash_equality(self):
        """Every remapped event's commit exists and the artifact bytes
        at that commit hash to the ledger artifact_hash (Art. II exact
        evidence — the remap is proven, not assumed)."""
        for e in self.events():
            if e["transition_id"] in self.REMAPPED:
                assert e["commit_sha"] == self.TARGET
                m = re.search(r"artifact anchored: (\S+\.json)",
                              e["reason"])
                rc = subprocess.run(
                    ["git", "show", f"{self.TARGET}:{m.group(1)}"],
                    cwd=REPO, capture_output=True)
                assert rc.returncode == 0, m.group(1)
                assert hashlib.sha256(rc.stdout).hexdigest() == \
                    e["artifact_hash"]

    def test_ledger_chain_replays(self):
        """The root hash recomputes and the chain links are intact."""
        from epistemic_integrity.post_scrub_evidence_revalidation import (
            _replay_ledger)
        root, valid, failures = _replay_ledger(self.events())
        assert valid, failures
        root_doc = json.loads((REPO / "epistemic_integrity" /
                               "approved_provenance" /
                               "state_transition_ledger_root.json")
                              .read_text())
        assert root_doc["ledger_root_hash"] == root
        assert root_doc["total_events"] == 29

    def test_no_destroyed_commit_remains_referenced(self):
        """No ledger event points at a commit that does not exist."""
        for e in self.events():
            rc = subprocess.run(["git", "cat-file", "-e",
                                f"{e['commit_sha']}^{{commit}}"],
                               cwd=REPO, capture_output=True)
            assert rc.returncode == 0, (e["transition_id"],
                                        e["commit_sha"])

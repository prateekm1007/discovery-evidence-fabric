"""tests/test_r452_preflight.py — the R452 Phase 0 regression battery.

The directive's stop rule: "do not proceed to the scientific phase
unless both identity defects are resolved and regression-tested."

The battery attacks the corrected capture parser and the contradiction
detector (Art. XVII: every control must have an attempted bypass):

  1. POSITIVE CONTROL — the real captured production ledger certifies
     the one authoritative run identity (31 RUN_OWNED lines).
  2. RUN-ID LAUNDERING — a valid run-owned ledger PLUS an
     unexpected/alternate run ID: the parser MUST FAIL CLOSED (both
     extract_run_identity's one-run-per-session rule and
     assert_no_foreign_run_ids' authoritative-set rule). This is the
     directive's explicitly required adversarial case.
  3. NULL RUN_ID — a RUN_OWNED line with run_id=null fails closed.
  4. SESSION LAUNDERING — a run-owned line carrying a foreign
     session_id fails closed.
  5. EMPTY SLICE — zero RUN_OWNED lines fails closed.
  6. KNOWN-DEFECT CONTROL — a replica of the R451 production record's
     defective shape (run_ids_found=[] + prose-ambiguous attack claim)
     is DETECTED by check_contradictions (the detector is exercised
     against the real, known defect, not just clean inputs).
  7. THE REAL ARTIFACTS — the committed R452/PREFLIGHT.json records
     both defects detected AND both fixes applied AND all identity
     assertions passing (the artifact-level regression).

Constitutional anchors: Art. III (the verifier never trusts the
claimant), Art. VI (provenance never manufactured), Art. XVI (code is
a hypothesis about enforcement; these tests are the evidence), Art.
XVII (attempted bypass), Art. XXI.4/Art. L (the known-defect control).
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from r452_preflight import (  # noqa: E402
    PreflightIdentityError,
    assert_no_foreign_run_ids,
    check_contradictions,
    extract_run_identity,
    rebuild_attack_adjudication_record,
    SESSION_ID,
)

CAPTURES = (REPO_ROOT / "R451" / "PRODUCTION_FRESH_RUN_C13" /
            f"{SESSION_ID}_ledger_lines.json")
PREFLIGHT_RECORD = REPO_ROOT / "R452" / "PREFLIGHT.json"

AUTHORITATIVE_RUN_ID = (
    "engrun:ui_40_000_vial_batches_protein_injectable_she_291053:"
    "2026-09-13T09:17:33")


def _line(**over):
    """A canonical run-owned ledger line (the real captured shape)."""
    base = {
        "run_id": AUTHORITATIVE_RUN_ID,
        "session_id": SESSION_ID,
        "request_id": "req-001",
        "stage": "SYNTHESIZE",
        "provider": "localqwen",
        "model": "qwen3-1.7b",
        "attempt": 1,
        "task": "STRONG",
        "cost_class": "ZERO_PAID_COST_SELF_HOSTED",
        "account_domain": "LOCAL_COMPUTE",
        "failure_class": None,
        "fallback_from": None,
        "fallback_to": None,
        "call_class": "RUN_OWNED",
        "capability_state": "PROBE_OK",
    }
    base.update(over)
    return base


class TestCaptureParserPositive(unittest.TestCase):
    def test_real_captured_ledger_certifies_identity(self):
        """POSITIVE CONTROL: the real 31-line captured production
        ledger certifies exactly the one authoritative run id."""
        lines = json.loads(CAPTURES.read_text())
        ident = extract_run_identity(lines, SESSION_ID)
        self.assertEqual(ident["run_ids_found"],
                         [AUTHORITATIVE_RUN_ID])
        self.assertEqual(ident["run_owned_lines"], 31)
        self.assertTrue(ident["invariant_run_owned_non_null_run_id"])
        self.assertTrue(ident["session_id_on_every_line"])
        self.assertEqual(ident["paid_cost_lines"], 0)

    def test_synthetic_valid_ledger_passes(self):
        ident = extract_run_identity([_line(), _line()], SESSION_ID)
        self.assertEqual(ident["run_ids_found"], [AUTHORITATIVE_RUN_ID])


class TestRunIdLaundering(unittest.TestCase):
    """THE DIRECTIVE'S REQUIRED ADVERSARIAL CASE: a valid run-owned
    ledger plus an unexpected/alternate run ID must FAIL."""

    def test_alternate_run_id_fails_extract(self):
        foreign = _line(run_id="engrun:DIFFERENT_RUN:2026-09-13")
        with self.assertRaises(PreflightIdentityError) as ctx:
            extract_run_identity(
                [_line(), _line(), foreign], SESSION_ID)
        self.assertIn("distinct run_ids", str(ctx.exception))

    def test_alternate_run_id_fails_authoritative_set(self):
        """A capture that mixes another run's lines into this run's
        provenance is refused even when the session matches (the
        laundering is precisely: another run, same session)."""
        foreign = _line(run_id="engrun:LAUNDERED_RUN:2026-09-13")
        with self.assertRaises(PreflightIdentityError) as ctx:
            assert_no_foreign_run_ids(
                [_line(), foreign], [AUTHORITATIVE_RUN_ID])
        self.assertIn("foreign run_id", str(ctx.exception))

    def test_null_run_id_fails_closed(self):
        with self.assertRaises(PreflightIdentityError) as ctx:
            extract_run_identity(
                [_line(), _line(run_id=None)], SESSION_ID)
        self.assertIn("null run_id", str(ctx.exception))

    def test_empty_run_id_fails_closed(self):
        with self.assertRaises(PreflightIdentityError):
            extract_run_identity(
                [_line(), _line(run_id="")], SESSION_ID)

    def test_session_mismatch_fails_closed(self):
        with self.assertRaises(PreflightIdentityError) as ctx:
            extract_run_identity(
                [_line(), _line(session_id="ts_FOREIGN")], SESSION_ID)
        self.assertIn("do not match the expected production session",
                      str(ctx.exception))

    def test_zero_run_owned_lines_fails_closed(self):
        probe_only = [_line(call_class="CAPABILITY_PROBE",
                            run_id=None)]
        with self.assertRaises(PreflightIdentityError) as ctx:
            extract_run_identity(probe_only, SESSION_ID)
        self.assertIn("no RUN_OWNED lines", str(ctx.exception))

    def test_capability_probe_lines_are_not_run_identity(self):
        """Probe lines legitimately carry run_id=null (C1.3-3) and are
        EXCLUDED from run-identity certification — mixing them in must
        neither crash the parser nor certify a null run id."""
        mixed = [_line(),
                 _line(call_class="CAPABILITY_PROBE", run_id=None),
                 _line(call_class="STANDALONE", run_id=None)]
        ident = extract_run_identity(mixed, SESSION_ID)
        self.assertEqual(ident["run_ids_found"], [AUTHORITATIVE_RUN_ID])
        # the authoritative-set check ignores non-run-owned lines
        assert_no_foreign_run_ids(mixed, [AUTHORITATIVE_RUN_ID])


class TestKnownDefectControl(unittest.TestCase):
    """The R451 production record's own defect shape, replicated: the
    DETECTOR must fire (a known-defect control for the instrument)."""

    REAL_ATTACK_RESULTS = {
        "adversarial_status": "NOT_RUN",
        "adversarial_not_run_reason": "EVIDENCE_GATE_FAILED",
        "transport": {"status": "NEVER_CALLED"},
        "attacks": [],
        "killed_count": 0,
        "overall": "NOT_RUN",
    }
    REAL_ADJUDICATION = {
        "council": {"verdict": "CONTESTED", "checks": [
            {"check": "evidence_span_verified", "result": False},
            {"check": "adversarial_not_killed", "result": False},
        ]},
        "evidence_verification": {
            "verified": False, "evidence_class": "UNSUPPORTED",
            "issues": ["missing_source_span",
                       "mechanism_span_not_verbatim"]},
    }

    def _rebuilt(self):
        identity = {"run_ids_found": [AUTHORITATIVE_RUN_ID]}
        atk = {"attack_results": self.REAL_ATTACK_RESULTS}
        adj = {"adjudication": self.REAL_ADJUDICATION}
        result_fields = {
            "adversarial_overall": "NOT_RUN",
            "adjudication_verdict": "CONTESTED",
        }
        phase_ledger = [
            {"stage": "ATTACK", "status": "OK"},
            {"stage": "ADJUDICATION", "status": "OK"},
        ]
        return rebuild_attack_adjudication_record(
            atk, adj, result_fields, phase_ledger, identity)

    def test_known_defect_shape_detected(self):
        """run_ids_found=[] + attack-prose ambiguity -> BOTH defects
        are detected (the instrument detects the real R451 defect)."""
        rebuilt = self._rebuilt()
        round_record = {"production_fresh_run": {"chain": {
            "attack": "the ATTACK stage EXECUTED (envelope persisted) "
                      "and the ADJUDICATION recorded verdict CONTESTED; "
                      "adversarial_overall=NOT_RUN (the endpoint's own "
                      "field)"}}}
        production_record = {"durable_provenance": {
            "run_ids_found": []},
            "chain": {"attack_overall": "NOT_RUN"}}
        defects = check_contradictions(rebuilt, round_record,
                                       production_record)
        kinds = {d["defect"] for d in defects}
        self.assertIn("RUN_IDS_FOUND_EMPTY_EXTRACTION_DEFECT", kinds)
        self.assertIn("ROUND_RECORD_ATTACK_PROSE_CONTRADICTS_STATE",
                      kinds)

    def test_adjudication_determination_true(self):
        rebuilt = self._rebuilt()
        self.assertTrue(rebuilt["adjudication"]
                        ["adjudication_occurred"])
        self.assertEqual(rebuilt["adjudication"]["verdict"],
                         "CONTESTED")
        self.assertEqual(rebuilt["adversarial_attack"]
                         ["not_run_reason"], "EVIDENCE_GATE_FAILED")
        self.assertEqual(rebuilt["adversarial_attack"]
                         ["transport_status"], "NEVER_CALLED")

    def test_clean_record_produces_no_run_identity_defect(self):
        """A correctly-extracted record produces no defects (fail-
        closed does not mean universal rejection — Art. V)."""
        rebuilt = self._rebuilt()
        round_record = {"production_fresh_run": {"chain": {
            "attack": "adversarial NEVER_CALLED "
                      "(EVIDENCE_GATE_FAILED); adjudication "
                      "CONTESTED"}}}
        production_record = {
            "durable_provenance": {
                "run_ids_found": [AUTHORITATIVE_RUN_ID]},
            "chain": {"attack_overall": "NOT_RUN",
                      "derived_attack_adjudication_record": {}}}
        defects = check_contradictions(rebuilt, round_record,
                                       production_record)
        kinds = {d["defect"] for d in defects}
        self.assertNotIn("RUN_IDS_FOUND_EMPTY_EXTRACTION_DEFECT",
                         kinds)
        self.assertNotIn(
            "ROUND_RECORD_ATTACK_PROSE_CONTRADICTS_STATE", kinds)

    def test_adversarial_overall_mismatch_detected(self):
        """If the result envelope claimed the attack RAN while the
        envelope says NEVER_CALLED, the contradiction fires."""
        rebuilt = self._rebuilt()
        rebuilt["adversarial_overall_sources_agree"] = False
        defects = check_contradictions(rebuilt, None, None)
        kinds = {d["defect"] for d in defects}
        self.assertIn("ADVERSARIAL_OVERALL_CONTRADICTS_ENVELOPE",
                      kinds)

    def test_verdict_without_execution_detected(self):
        rebuilt = self._rebuilt()
        rebuilt["adjudication"]["adjudication_occurred"] = False
        rebuilt["adjudication"]["verdict"] = "CONTESTED"
        defects = check_contradictions(rebuilt, None, None)
        kinds = {d["defect"] for d in defects}
        self.assertIn("ADJUDICATION_VERDICT_WITHOUT_EXECUTION", kinds)


class TestRealArtifacts(unittest.TestCase):
    """The committed preflight artifact itself is regression-checked
    (Art. X: the artifacts are the authority)."""

    def test_preflight_record_passes_with_both_fixes(self):
        doc = json.loads(PREFLIGHT_RECORD.read_text())
        self.assertEqual(doc["status"], "PASS")
        self.assertEqual(
            doc["adjudication_determination"]
            ["adjudication_occurred"], True)
        self.assertEqual(
            doc["adjudication_determination"]["verdict"], "CONTESTED")
        self.assertEqual(
            doc["rebuilt_attack_adjudication_record"]
            ["adversarial_attack"]["not_run_reason"],
            "EVIDENCE_GATE_FAILED")
        fixes = {f["fix"] for f in doc["fix_events"]}
        self.assertIn("RUN_IDENTITY_EXTRACTED_FROM_LEDGER", fixes)
        self.assertIn("DERIVED_ATTACK_ADJUDICATION_RECORD_REBUILT",
                      fixes)
        for k, v in doc["identity_assertions"].items():
            self.assertTrue(v, f"identity assertion {k} failed")

    def test_production_record_now_carries_derived_record(self):
        prod = json.loads(
            (REPO_ROOT / "R451" / "PRODUCTION_FRESH_RUN_C13.json")
            .read_text())
        dp = prod["durable_provenance"]
        self.assertEqual(dp["run_ids_found"], [AUTHORITATIVE_RUN_ID])
        chain = prod["chain"]
        self.assertIn("derived_attack_adjudication_record", chain)
        self.assertTrue(chain["adjudication_occurred"])
        self.assertEqual(chain["adjudication_verdict"], "CONTESTED")
        remed = prod["r452_preflight_remediation"]
        self.assertEqual(len(remed["defects_detected"]), 2)
        self.assertEqual(len(remed["fix_events"]), 2)

    def test_authoritative_extract_committed(self):
        ext = json.loads((REPO_ROOT / "R452" /
                          "AUTHORITATIVE_RUN_STATE_EXTRACT.json")
                         .read_text())
        self.assertEqual(ext["run_identity"]["run_ids_found"],
                         [AUTHORITATIVE_RUN_ID])
        self.assertEqual(
            ext["attack_envelope_extract"]["attack_results"]
            ["adversarial_not_run_reason"], "EVIDENCE_GATE_FAILED")
        self.assertEqual(
            ext["adjudication_envelope_extract"]["adjudication"]
            ["council"]["verdict"], "CONTESTED")


if __name__ == "__main__":
    unittest.main()

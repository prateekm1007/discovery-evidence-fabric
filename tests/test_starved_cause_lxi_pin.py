"""tests/test_starved_cause_lxi_pin.py — hermetic zero-LLM pins for the
typed mechanism-space starvation cause (owner capability round
2026-11-12, item 4; Art. LXI — infrastructure failure is never
scientific rejection; Art. XXV — unknown stays unknown; Art. XXVII —
no threshold invention).

ROOT CAUSE (pinned here): GENERATION_NO_OPERATOR_CONTRACT was the
scorer's label for the p05/new02 starved records, because the
production lean mechanism-space paths record NOTHING when no operator
runs — zero operator_results in the envelope is the shared shape of
every evidence-starvation path (upstream chain cut by a 429/timeout,
an empty frozen plane, a custody join-miss, or a true
contract-mismatch). The scorer therefore mislabeled infrastructure
starvation as a generation-contract failure.

THE FIX (pinned here): each production no-generation path records ONE
typed `starved_cause` on the mechanism-space envelope (label + LXI
class + measured join diagnostics — zero LLM calls, exact-record
checks, no invented thresholds); the scorer's `_funnel_row` reads the
record and falls back to the legacy state vocabulary / labels for
envelopes that predate it (the legacy mislabel is kept only as the
last-resort shape).

Hermetic: the SKIPPED and NO_EVIDENCE paths refuse before any
instantiation call; the no-match path satisfies zero operator
contracts, so it makes zero operator calls (the LLM fake records
calls and the pins assert zero).
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from discovery_fabric.engine import adapters  # noqa: E402
from discovery_fabric.engine import mechanism_space as _ms_mod  # noqa: E402
from discovery_fabric.engine.candidate import Candidate  # noqa: E402

# -----------------------------------------------------------------
# fixture vocabulary (disjoint on purpose: the no-match case must
# satisfy ZERO operator admission contracts)
# -----------------------------------------------------------------
PROBLEM = {
    "problem_id": "starved-pin",
    "device": "quartz oscillator assembly",
    "failure": "reference frequency drift during storage",
    "failure_mode": "",
    "constraint": "",
}

# abstract words avoid the geometry/boundary vocabs and all problem
# failure terms (verified against the mechanism_space vocab tables):
# system terms are disjoint from the device terms, mechanism terms
# from the failure terms, boundary_conditions absent, failure_mode
# absent (the lean item carries only system/abstract/mechanism/
# observed_effect).
FROZEN_REC = {
    "id": "s1",
    "title": "Coralline algae reef framework study",
    "abstract": ("Coralline algae grow faster than sediment resupply "
                 "replaces lost reef material, smothering early life "
                 "stages."),
    "content_hash": "h_s1",
    "retrieval_timestamp": "2026-11-12T00:00:00Z",
    "source": "europepmc",
}

CLEAN_LEDGER = [
    {"stage": "RETRIEVE", "status": "OK"},
    {"stage": "FREEZE", "status": "OK"},
    {"stage": "VERIFY", "status": "OK"},
]


def _cls(rid, classification):
    return {"source_id": rid, "classification": classification}


def _env(records, classes, ledger=None, ec_error=None):
    env = Candidate(problem=dict(PROBLEM),
                    problem_id="starved-pin-test")
    env.evidence = list(records)
    ec = {"n_items": len(records), "items": list(classes)}
    if ec_error is not None:
        ec["error"] = ec_error
    env.evidence_classification = ec
    if ledger is not None:
        env.stage_log = [dict(e) for e in ledger]
    return env


def _no_cemetery():
    return mock.patch(
        "orchestrator.mechanism_cemetery.check_candidate_against_cemetery",
        return_value={"hard_blocks": [], "warnings": [],
                      "informational": [],
                      "total_lessons_consulted": 0,
                      "verdict": "PROCEED"})


def _execute(env, ledger=None):
    """Drive the MS adapter's execute with a recording LLM fake + the
    cemetery mock. Returns (res, llm_calls)."""
    calls = []

    def _fake(prompt, system="", **kw):
        calls.append(kw.get("purpose", "?"))
        return {"ok": True, "status": "OK", "content": "",
                "provider": "fake", "model": "fake",
                "prompt_hash": "h", "output_hash": "h",
                "call_provenance": {}, "cost_provenance": {},
                "task_degradation": {}}

    if ledger is not None:
        env.stage_log = [dict(e) for e in ledger]
    with mock.patch.object(_ms_mod, "llm_generate", side_effect=_fake), \
            _no_cemetery():
        res = adapters.MechanismSpaceAdapter().execute(
            env, {"run_id": "starved-pin"})
    return res, calls


# -----------------------------------------------------------------
# 1. the classifier itself (exact-record checks, no thresholds)
# -----------------------------------------------------------------
class TestStarvedCauseClassifier(unittest.TestCase):
    def test_clean_chain_empty_plane_is_data_failure(self):
        env = _env([], [], ledger=CLEAN_LEDGER)
        env.evidence_classification = None  # a genuinely absent record
        c = adapters._ms_starved_cause(env, "NO_EVIDENCE")
        self.assertEqual(c["lxi_class"], "INCOMPLETE_DATA_FAILURE")
        self.assertEqual(c["diagnostics"]["verify_classification_state"],
                         "ABSENT")
        self.assertEqual(c["diagnostics"]["n_frozen_records"], 0)

    def test_failed_verify_stage_is_infra_failure(self):
        ledger = [{"stage": "RETRIEVE", "status": "OK"},
                  {"stage": "FREEZE", "status": "OK"},
                  {"stage": "VERIFY", "status": "FAILED_EXPLICIT",
                   "error": "LLMTransportError: 429 quota"}]
        env = _env([], [], ledger=ledger)
        self.assertEqual(
            adapters._ms_starved_cause(env, "NO_EVIDENCE")["lxi_class"],
            "INCOMPLETE_INFRASTRUCTURE_FAILURE")

    def test_policy_skipped_upstream_is_infra_failure(self):
        ledger = [{"stage": "RETRIEVE", "status": "SKIPPED_POLICY_LOW_VALUE",
                   "skip_reason": "x"},
                  {"stage": "FREEZE", "status": "OK"},
                  {"stage": "VERIFY", "status": "OK"}]
        env = _env([], [], ledger=ledger)
        self.assertEqual(
            adapters._ms_starved_cause(env, "NO_EVIDENCE")["lxi_class"],
            "INCOMPLETE_INFRASTRUCTURE_FAILURE")

    def test_classifier_error_record_is_infra_failure(self):
        env = _env([dict(FROZEN_REC)], [_cls("s1", "DIRECT_SUPPORT")],
                   ledger=CLEAN_LEDGER,
                   ec_error="LLMTransportError: 429 quota")
        c = adapters._ms_starved_cause(env, "NO_EVIDENCE")
        self.assertEqual(c["lxi_class"], "INCOMPLETE_INFRASTRUCTURE_FAILURE")
        self.assertEqual(
            c["diagnostics"]["verify_classification_state"],
            "CLASSIFIER_ERROR")

    def test_examined_not_supporting_is_scientific(self):
        env = _env([dict(FROZEN_REC)], [_cls("s1", "IRRELEVANT")],
                   ledger=CLEAN_LEDGER)
        c = adapters._ms_starved_cause(env, "NO_EVIDENCE")
        self.assertEqual(c["lxi_class"], "REJECTED_EVIDENCE")
        self.assertEqual(c["diagnostics"]["n_verified_items"], 0)

    def test_custody_join_miss_is_data_failure(self):
        # the classifier examined a record the frozen custody set does
        # not hold: an unknown, never re-fabricated onto the plane
        env = _env([dict(FROZEN_REC)], [_cls("s9", "DIRECT_SUPPORT")],
                   ledger=CLEAN_LEDGER)
        c = adapters._ms_starved_cause(env, "NO_EVIDENCE")
        self.assertEqual(c["lxi_class"], "INCOMPLETE_DATA_FAILURE")
        self.assertEqual(c["diagnostics"]["n_verified_items"], 1)
        self.assertEqual(c["diagnostics"]["n_join_misses"], 1)

    def test_unlogged_chain_never_reads_as_clean(self):
        # no stage ledger at all: the chain's upstream state is
        # unknown — unknown stays unknown (XXV), it is never claimed
        # as a scientific verdict.
        env = _env([dict(FROZEN_REC)], [_cls("s1", "IRRELEVANT")])
        self.assertEqual(
            adapters._ms_starved_cause(env, "NO_EVIDENCE")["lxi_class"],
            "INCOMPLETE_INFRASTRUCTURE_FAILURE")


# -----------------------------------------------------------------
# 2. the production no-generation paths record the cause
# -----------------------------------------------------------------
class TestProductionPathsRecordCause(unittest.TestCase):
    def test_skipped_path_records_cause_zero_calls(self):
        env = _env([], [], ledger=CLEAN_LEDGER)
        res, calls = _execute(env)
        space = res["apply_to"]["mechanism_space"]
        self.assertEqual(space["state"],
                         "SKIPPED_EVIDENCE_VERIFICATION_FAILED")
        self.assertEqual(calls, [])
        cause = space["starved_cause"]
        self.assertEqual(cause["label"],
                         "SKIPPED_EVIDENCE_VERIFICATION_FAILED")
        # clean ledger + empty plane: the DATA-plane class, not the
        # infra class (the classifier's own record states decide)
        self.assertEqual(cause["lxi_class"], "INCOMPLETE_DATA_FAILURE")

    def test_no_evidence_custody_miss_records_cause(self):
        env = _env([dict(FROZEN_REC)], [_cls("s9", "DIRECT_SUPPORT")],
                   ledger=CLEAN_LEDGER)
        res, calls = _execute(env)
        space = res["apply_to"]["mechanism_space"]
        self.assertEqual(space["state"], "NO_EVIDENCE")
        self.assertEqual(calls, [])
        cause = space["starved_cause"]
        self.assertEqual(cause["label"], "NO_EVIDENCE")
        self.assertEqual(cause["lxi_class"], "INCOMPLETE_DATA_FAILURE")
        self.assertEqual(cause["diagnostics"]["n_join_misses"], 1)

    def test_no_match_records_contradiction_free_cause(self):
        # verified + joined item, zero operator contract satisfied:
        # a SCIENTIFIC evidence verdict on the clean chain — the
        # label the old scorer reported as GENERATION_NO_OPERATOR_
        # CONTRACT.
        env = _env([dict(FROZEN_REC)], [_cls("s1", "DIRECT_SUPPORT")],
                   ledger=CLEAN_LEDGER)
        res, calls = _execute(env)
        space = res["apply_to"]["mechanism_space"]
        self.assertEqual(space["state"], "NO_CANDIDATES")
        # R6 OWNER AUDIT ROUND 2026-11-12 (directive 3): zero
        # EVIDENCE-anchored operator calls on no-match; the knowledge-
        # first generator (evidence-independent, anchor = the user's
        # problem statement) always runs — the canned empty response
        # parses zero blocks, so no candidate is fabricated.
        evidence_calls = [c for c in calls
                          if c != "operator_DOMAIN_KNOWLEDGE_FIRST"]
        self.assertEqual(evidence_calls, [],
                         "zero evidence-anchored operator calls on "
                         "no-match")
        self.assertEqual(calls, ["operator_DOMAIN_KNOWLEDGE_FIRST"])
        evidence_results = [o for o in space["operator_results"]
                            if o.get("operator")
                            != "DOMAIN_KNOWLEDGE_FIRST"]
        self.assertEqual(evidence_results, [])
        cause = space["starved_cause"]
        self.assertEqual(cause["label"], "NO_APPLICABLE_EVIDENCE")
        self.assertEqual(cause["lxi_class"], "REJECTED_EVIDENCE")

    def test_cut_chain_overrides_scientific_verdict(self):
        # the same scientific fixture, but the ledger records a cut
        # upstream stage: the starvation is attributed to the chain,
        # never to a verdict about the mechanism (Art. LXI).
        ledger = [{"stage": "RETRIEVE", "status": "FAILED_EXPLICIT",
                   "error": "timeout"},
                  {"stage": "FREEZE", "status": "OK"},
                  {"stage": "VERIFY", "status": "OK"}]
        env = _env([dict(FROZEN_REC)], [_cls("s1", "DIRECT_SUPPORT")],
                   ledger=ledger)
        res, _ = _execute(env)
        space = res["apply_to"]["mechanism_space"]
        self.assertEqual(space["state"], "NO_CANDIDATES")
        self.assertEqual(
            space["starved_cause"]["lxi_class"],
            "INCOMPLETE_INFRASTRUCTURE_FAILURE")
        self.assertEqual(
            space["starved_cause"]["diagnostics"]
            ["upstream_stage_statuses"]["RETRIEVE"], "FAILED_EXPLICIT")


# -----------------------------------------------------------------
# 3. the scorer's starved_reason ladder (legacy fallback preserved)
# -----------------------------------------------------------------
class TestScorerStarvedReasonLadder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import eval.run as _er  # noqa: F401  (import-safe: main guard)
        cls._er = _er

    def _row(self, ms_body, with_envelope=True,
             final_status="MECHANISM_STARVED"):
        import tempfile
        root = Path(tempfile.mkdtemp(prefix="starvedpin_"))
        pipe = root / "pipeline"
        pipe.mkdir()
        (pipe / "final_state.json").write_text(
            json.dumps({"final_status": final_status}), encoding="utf-8")
        if with_envelope:
            (pipe / "envelope_MECHANISM_SPACE.json").write_text(
                json.dumps({"mechanism_space": ms_body}),
                encoding="utf-8")
        row = self._er._funnel_row(root)
        import shutil
        shutil.rmtree(root, ignore_errors=True)
        return row

    def test_recorded_cause_label_wins(self):
        row = self._row({
            "n_candidates_generated": 0,
            "state": "NO_EVIDENCE",
            "starved_cause": {"label": "NO_EVIDENCE",
                              "lxi_class": "INCOMPLETE_DATA_FAILURE",
                              "diagnostics": {}}})
        self.assertEqual(row["starved_reason"], "NO_EVIDENCE")

    def test_recorded_skipped_label_wins(self):
        row = self._row({
            "n_candidates_generated": 0,
            "state": "SKIPPED_EVIDENCE_VERIFICATION_FAILED",
            "starved_cause": {"label": "SKIPPED_EVIDENCE_VERIFICATION_FAILED",
                              "lxi_class": "INCOMPLETE_INFRASTRUCTURE_FAILURE",
                              "diagnostics": {}}})
        self.assertEqual(row["starved_reason"],
                         "SKIPPED_EVIDENCE_VERIFICATION_FAILED")

    def test_legacy_state_vocabulary_fallback(self):
        # pre-fix envelopes carry the typed state without the cause
        # record: the state itself is the honest label.
        row = self._row({"n_candidates_generated": 0,
                         "state": "NO_EVIDENCE"})
        self.assertEqual(row["starved_reason"], "NO_EVIDENCE")

    def test_legacy_ops_contract_mismatch_fallback(self):
        row = self._row({
            "n_candidates_generated": 0,
            "state": "NO_CANDIDATES",
            "operator_results": [{"operator": "NONE",
                                  "state": "NO_APPLICABLE_EVIDENCE"}]})
        self.assertEqual(row["starved_reason"], "NO_APPLICABLE_EVIDENCE")

    def test_legacy_empty_envelope_keeps_last_resort_label(self):
        row = self._row({})
        self.assertEqual(row["starved_reason"],
                         "GENERATION_NO_OPERATOR_CONTRACT")

    def test_legacy_residual_ops_state_stays_unknown(self):
        row = self._row({
            "n_candidates_generated": 0,
            "state": "NO_CANDIDATES",
            "operator_results": [{"operator": "X",
                                  "state": "SOMETHING_UNTYPED"}]})
        self.assertEqual(row["starved_reason"], "UNKNOWN")

    def test_missing_envelope_starved_final_status(self):
        row = self._row({}, with_envelope=False)
        self.assertEqual(row["starved_reason"],
                         "NO_MECHANISM_SPACE_ENVELOPE")


if __name__ == "__main__":
    unittest.main()

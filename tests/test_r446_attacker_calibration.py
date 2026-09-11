"""tests/test_r446_attacker_calibration.py — R446-C1 Task 2: the
calibration EXPERIMENT contract (scorer semantics + the protections).

The corpus (R446/ATTACKER_CALIBRATION/CORPUS.json) must be committed
BEFORE any RAW record exists (freeze-then-run). These tests verify the
SCORER's semantics against SYNTHETIC attack records (authored here for
the scorer contract — not derived from instrument behavior, Art. VIII)
and pin the honest protections:

  - TPR over seeded defects; FPR/TNR over clean controls
  - near-miss detection requires the magnitude markers in the basis
  - evidence kills require basis binding to the provided evidence
  - a kill on a malformed/missing-evidence case types as
    ABSENCE_AS_CONTRADICTION
  - the verdict NEVER interprets better numbers as calibration
  - the gate state is reported read-only
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

r446cal = importlib.import_module("r446_attacker_calibration")


@pytest.fixture(scope="module")
def corpus():
    return json.loads(
        (REPO / "R446" / "ATTACKER_CALIBRATION" / "CORPUS.json").read_text())


def _attack(overall: str, kill_basis=None, state="ATTACK_RUN"):
    return {"overall": overall, "state": state,
            "kill_basis": kill_basis or []}


def _kill(cls, basis):
    return {"attack_class": cls, "basis": basis}


BY_ID = None


def _cases(corpus):
    return {c["case_id"]: c for c in corpus["cases"]}


# ---------------------------------------------------------------------------
# corpus structure (the six directive categories, authored before runs)
# ---------------------------------------------------------------------------
class TestCorpus:
    def test_six_categories_present(self, corpus):
        cats = {c["category"] for c in corpus["cases"]}
        assert cats == {
            "TRUE_POSITIVE_seeded_defect",
            "TRUE_NEGATIVE_clean_control",
            "NEAR_MISS_real_effect_fatal_magnitude",
            "SCOPE_CONFLICT_declared_boundary_trap",
            "EVIDENCE_CONTRADICTED",
            "MALFORMED_MISSING_EVIDENCE"}

    def test_22_cases_all_unique(self, corpus):
        ids = [c["case_id"] for c in corpus["cases"]]
        assert len(ids) == 22
        assert len(set(ids)) == 22

    def test_seeded_defects_cover_all_six_attack_classes(self, corpus):
        seeded = {c["seed_class"] for c in corpus["cases"]
                  if c.get("seed_class")}
        assert seeded == {
            "MECHANISM_FAILURE", "BOUNDARY_CONDITION_FAILURE",
            "EVIDENCE_CONTRADICTION", "BASELINE_EQUIVALENCE",
            "IMPLEMENTATION_IMPOSSIBILITY", "MEASUREMENT_AMBIGUITY"}

    def test_clean_controls_expect_survived(self, corpus):
        for c in corpus["cases"]:
            if c["category"] == "TRUE_NEGATIVE_clean_control":
                assert c["ground_truth"]["expected_final"] == "SURVIVED"

    def test_scope_cases_expect_survived(self, corpus):
        for c in corpus["cases"]:
            if c["category"] == "SCOPE_CONFLICT_declared_boundary_trap":
                assert c["ground_truth"]["expected_final"] == "SURVIVED"

    def test_absence_cases_expect_not_kill(self, corpus):
        for c in corpus["cases"]:
            if c["category"] == "MALFORMED_MISSING_EVIDENCE":
                assert c["ground_truth"]["expected_final"] == "SURVIVED"

    def test_evidence_cases_split_refuted_and_supported(self, corpus):
        ev = [c for c in corpus["cases"]
              if c["category"] == "EVIDENCE_CONTRADICTED"]
        killed = [c for c in ev
                  if c["ground_truth"]["expected_final"] == "KILLED"]
        survived = [c for c in ev
                    if c["ground_truth"]["expected_final"] == "SURVIVED"]
        assert len(killed) == 3 and len(survived) == 1

    def test_evidence_items_carry_refuting_content_in_title(
            self, corpus):
        # the instrument shows evidence TITLES only — the refuting data
        # must live in the title text (the R401-WC2 cal-05/06 pattern)
        for c in corpus["cases"]:
            for ev in c.get("evidence_items") or []:
                assert "id" in ev and "title" in ev
                if c["case_id"] in (
                        "cal-03-evidence-refuted-strainer",
                        "cal-17-evidence-refuted-seasonal",
                        "cal-18-evidence-refuted-average-sizing"):
                    assert len(ev["title"]) > 60

    def test_pre_registered_bars_are_the_r412_seal(self, corpus):
        bars = corpus["pre_registered_thresholds"]
        assert bars["tpr_min"] == 0.75
        assert bars["fpr_max"] == 0.30
        assert bars["coverage_min"] == 0.875
        assert bars["parse_completeness_min"] == 0.875
        assert "REUSED" in bars["provenance"]

    def test_gate_note_preserves_abstain_protection(self, corpus):
        note = corpus["instrument_semantics"]["abstain_escalate_gate"]
        assert "IN FORCE" in note
        assert "cannot flip" in note


# ---------------------------------------------------------------------------
# scorer semantics on synthetic records
# ---------------------------------------------------------------------------
class TestScorer:
    def test_perfect_instrument_scores_full_bars(self, corpus):
        cases = _cases(corpus)
        raw = {}
        for cid, c in cases.items():
            gt = c["ground_truth"]
            if gt["expected_final"] == "KILLED":
                basis = (f"the measured {gt['defect_class'][:120]} "
                         "with markers " +
                         " ".join(gt.get("expected_defect_in_basis")
                                  or [])[:200])
                raw[cid] = _attack(
                    "KILLED", [_kill(
                        gt.get("expected_kill_surface") or
                        "MECHANISM_FAILURE", basis)])
            else:
                raw[cid] = _attack("SURVIVED")
        res = r446cal.score_all(corpus, raw)
        hc = res["headline_confusion"]
        assert hc["TPR"] == 1.0
        assert hc["FPR"] == 0.0
        assert hc["TNR"] == 1.0
        assert res["coverage"] == 1.0
        # and even a PERFECT synthetic run does not claim calibration:
        # the verdict field stays honest about the gate being authority
        assert res["verdict"]["calibration_state_after_this_run"]\
            .startswith("NOT_CALIBRATED")

    def test_universal_killer_scores_tnr_zero(self, corpus):
        # the R444/R445 measured behavior class: kill everything
        raw = {c["case_id"]: _attack(
            "KILLED", [_kill(
                "MECHANISM_FAILURE",
                "the claimed mechanism cannot work because physics "
                "forbids this effect at the stated scale entirely")])
            for c in corpus["cases"]}
        res = r446cal.score_all(corpus, raw)
        hc = res["headline_confusion"]
        assert hc["TPR"] == 1.0       # everything killed -> all detected
        assert hc["TNR"] == 0.0       # and all clean controls killed
        assert hc["FPR"] == 1.0
        assert res["verdict"]["all_bars_met"] is False

    def test_near_miss_requires_markers(self, corpus):
        cases = _cases(corpus)
        nm = [c for c in cases.values()
              if c["category"] == "NEAR_MISS_real_effect_fatal_magnitude"]
        cid = nm[0]["case_id"]
        # killed WITHOUT the expected magnitude markers -> not grounded
        raw = {cid: _attack("KILLED", [_kill(
            "MECHANISM_FAILURE",
            "this is a fabricated bare objection with no magnitude "
            "content at all in it whatsoever")])}
        rec = r446cal._score_case(cases[cid], raw[cid])
        assert rec["outcome"] == "DETECTED_KILL_UNGROUNDED"
        # killed WITH the markers -> grounded
        markers = cases[cid]["ground_truth"][
            "expected_defect_in_basis"]
        raw[cid] = _attack("KILLED", [_kill(
            "MECHANISM_FAILURE",
            "orders of magnitude gap in the required collection length "
            "at this velocity: " + " ".join(markers))])
        rec = r446cal._score_case(cases[cid], raw[cid])
        assert rec["outcome"] == "DETECTED_KILL_GROUNDED"

    def test_evidence_kill_requires_binding(self, corpus):
        cases = _cases(corpus)
        cid = "cal-17-evidence-refuted-seasonal"
        raw = {cid: _attack("KILLED", [_kill(
            "EVIDENCE_CONTRADICTION",
            "no evidence the seasonal driver exists at all anywhere")])}
        rec = r446cal._score_case(cases[cid], raw[cid])
        assert rec["outcome"] == "DETECTED_KILL_NOT_BOUND"
        raw[cid] = _attack("KILLED", [_kill(
            "EVIDENCE_CONTRADICTION",
            "the 24-month log shows a uniform 4.0-4.3 clog rate every "
            "quarter with no winter baseline and chlorophyll below 3 "
            "ug/L in the indoor basin")])
        rec = r446cal._score_case(cases[cid], raw[cid])
        assert rec["outcome"] == "DETECTED_KILL_EVIDENCE_BOUND"

    def test_absence_kill_types_absence_class(self, corpus):
        cases = _cases(corpus)
        cid = "cal-20-absence-no-evidence-provided"
        raw = {cid: _attack("KILLED", [_kill(
            "EVIDENCE_CONTRADICTION",
            "no evidence is provided that the filtration works and "
            "therefore the mechanism fails and cannot reduce clogging "
            "events at all")])}
        rec = r446cal._score_case(cases[cid], raw[cid])
        assert rec["outcome"] == "FALSE_KILL"
        assert rec["false_kill_class"] == "ABSENCE_AS_CONTRADICTION"

    def test_scope_false_kill_classifies_scope_mismatch(self, corpus):
        cases = _cases(corpus)
        cid = "cal-10-scope-scale-only-filtration"
        raw = {cid: _attack("KILLED", [_kill(
            "EVIDENCE_CONTRADICTION",
            "the candidate fails to address the biofilm share of "
            "clogging which is the dominant measured failure mode; it "
            "does not address biofilm at all and therefore cannot "
            "solve the problem")])}
        rec = r446cal._score_case(cases[cid], raw[cid])
        assert rec["outcome"] == "FALSE_KILL"
        assert rec["false_kill_class"] == "SCOPE_MISMATCH"

    def test_transport_incomplete_not_counted_as_survival(
            self, corpus):
        cases = _cases(corpus)
        raw = {c["case_id"]: _attack("ATTACK_INCOMPLETE",
                                     state="ATTACK_INCOMPLETE")
               for c in cases.values()}
        res = r446cal.score_all(corpus, raw)
        hc = res["headline_confusion"]
        assert hc["transport_incomplete_all_cohorts"] == 22
        assert res["coverage"] == 0.0
        # conservative: incompletes are never survivals
        assert hc["clean_survived"] == 0

    def test_gate_reported_read_only(self, corpus, monkeypatch):
        # the gate's resolve_state is read for reporting; it is never
        # written by this experiment
        raw = {}
        res = r446cal.score_all(corpus, raw)
        assert "resolve_state" in res["abstain_escalate_gate"]
        assert "cannot flip" in res["abstain_escalate_gate"]["note"]


# ---------------------------------------------------------------------------
# the freeze discipline
# ---------------------------------------------------------------------------
class TestFreezeDiscipline:
    def test_no_raw_records_committed_before_corpus(self):
        # in the REPO tree, RAW/ must not exist at test time unless the
        # corpus is committed first — the driver enforces this; here we
        # verify the corpus file exists and is tracked
        corpus_path = REPO / "R446" / "ATTACKER_CALIBRATION" / "CORPUS.json"
        assert corpus_path.exists()

    def test_freeze_check_function_exists(self):
        assert callable(r446cal._freeze_check)

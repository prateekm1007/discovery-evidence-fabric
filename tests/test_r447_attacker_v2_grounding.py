"""R447 Attacker v2 — the grounding-discipline battery (Phase 6).

Operator directive R447-C1 Phase 6: the attacker's KILL must pass the
grounding check (evidence / computation / record / declared-scope
binding) before it carries terminal verdict authority; an ungrounded
or absence-grounded KILL becomes ABSTAIN with the objection preserved
and ESCALATED. The corpus, its thresholds, and the clean controls are
UNTOUCHED (the rerun driver consumes the frozen corpus verbatim).

Battery:
  * the four bindings each ground a KILL (mechanically verified)
  * absence grounds NEVER ground a kill (Art. XXI.3/XXV)
  * ungrounded kills demote to ABSTAIN (objection preserved verbatim,
    escalated; never dropped, never re-labelled RISK)
  * overall: KILLED iff a grounded kill; ESCALATED_OBJECTION iff only
    demoted kills; UNCERTAIN iff RISK/INVALID; SURVIVED otherwise
  * the gate composes: a v2 KILLED record consults the v2 measurement
    (absent -> fail-closed UNKNOWN_NOT_CALIBRATED -> escalated at
    consumption); v1 records keep consulting the R412/R417 measurement
  * parse discipline: the GROUNDED_IN tail rides the same line without
    breaking the six-field parse
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import independent_attack as ia  # noqa: E402
from discovery_fabric.engine import attacker_calibration as ac  # noqa: E402


CAND = {
    "candidate_id": "cal-fixture",
    "mechanism": ("a swirl-vortex nozzle centrifuges scale particles "
                  "away from the throat wall during operation"),
    "intervention": "retrofit swirl insert in the 150 mm supply line",
    "predicted_effect": ("clogging events per campaign reduced from "
                         "4.1 to below 0.6"),
    "testable_prediction": "split-header trial shows 85 percent fewer",
    "novel_design_variable": "vane count",
    "known_failure_modes": ["erosion at high velocity"],
    "constraint_set": {
        "boundary_conditions": "recirculated water at 32-38 C, 14 bar",
    },
}
EV = [{
    "id": "ev-1",
    "title": "Metallurgical analysis of 40 clogged nozzles",
    "abstract": "70 percent of blockages are biofilm-slime, not scale",
}]


class TestGroundingCheck:
    def test_evidence_binding_grounds(self):
        basis = ("The metallurgical analysis of 40 clogged nozzles "
                 "shows 70 percent of blockages are biofilm-slime, "
                 "contradicting the claimed scale-removal effect "
                 "GROUNDED_IN: EVIDENCE ev-1")
        g = ia.grounding_check(basis, CAND, EV)
        assert g["grounded"]
        assert any(b["binding"] == "evidence" for b in g["bindings"])

    def test_computation_binding_grounds(self):
        basis = ("operates at 14 bar static pressure, which exceeds the "
                 "10 bar differential rating of the transducers — the "
                 "component fails at the declared operating point "
                 "GROUNDED_IN: COMPUTATION 14 bar > 10 bar rating")
        g = ia.grounding_check(basis, CAND, EV)
        assert g["grounded"]
        assert any(b["binding"] == "computation" for b in g["bindings"])

    def test_record_binding_grounds(self):
        basis = ("the claim that the swirl-vortex nozzle centrifuges "
                 "scale particles away from the throat wall is "
                 "contradicted by the retained-particle measurement "
                 "GROUNDED_IN: RECORD \"centrifuges scale particles "
                 "away from the throat wall\"")
        g = ia.grounding_check(basis, CAND, EV)
        assert g["grounded"]
        assert any(b["binding"] == "record" for b in g["bindings"])

    def test_scope_binding_grounds(self):
        basis = ("the design assumes recirculated water at 32-38 C "
                 "with 14 bar supply, but the dosing limit at 11 bar "
                 "makes the declared regime unreachable "
                 "GROUNDED_IN: SCOPE 14 bar supply clause")
        g = ia.grounding_check(basis, CAND, EV)
        assert g["grounded"]
        assert any(b["binding"] == "declared_scope" for b in g["bindings"])

    def test_absence_ground_never_grounds(self):
        for basis in (
            "The candidate fails to provide any scientific evidence "
            "or credible references to support the claimed mechanism",
            "The candidate has no evidence bundle to support their "
            "claims, which makes it impossible to verify the effect",
            "The candidate fails to demonstrate superiority over the "
            "baseline with any experimental data",
            "There is an absence of any empirical validation of the "
            "predicted reduction",
        ):
            g = ia.grounding_check(basis, CAND, EV)
            assert g["absence_ground"], basis
            assert not g["grounded"], basis

    def test_bare_assertion_ungrounded(self):
        basis = ("This mechanism is not fundamentally different from "
                 "the baseline and the design will not work in "
                 "practice for this application at all")
        g = ia.grounding_check(basis, CAND, EV)
        assert not g["grounded"]
        assert "no evidence / computation / record / declared-scope" \
            in g["demotion_reason"]

    def test_claimed_binding_alone_is_recorded_not_trusted(self):
        """A GROUNDED_IN declaration the check cannot VERIFY is
        recorded verbatim but grounds nothing (Art. III: the verifier
        never trusts the claimant)."""
        basis = ("The mechanism is impossible "
                 "GROUNDED_IN: EVIDENCE ev-999-does-not-exist")
        g = ia.grounding_check(basis, CAND, EV)
        assert g["claimed_ground"]
        assert not g["grounded"]


class TestDemotionSemantics:
    def _items(self, content, cand=CAND, ev=EV):
        return ia._validate_parsed(ia._parse_attack(content), cand, ev)

    GROUNDED_KILL = (
        "MECHANISM_FAILURE: KILL — the metallurgical analysis of 40 "
        "clogged nozzles shows 70 percent of blockages are biofilm-"
        "slime, contradicting the scale-removal claim "
        "GROUNDED_IN: EVIDENCE ev-1\n")
    UNGROUNDED_KILL = (
        "MECHANISM_FAILURE: KILL — the candidate fails to provide any "
        "scientific evidence or credible references to support the "
        "claimed mechanism GROUNDED_IN: EVIDENCE none-held\n")

    def test_grounded_kill_stands(self):
        items = self._items(self.GROUNDED_KILL + (
            "BOUNDARY_CONDITION_FAILURE: SURVIVE — none\n"
            "EVIDENCE_CONTRADICTION: SURVIVE — none\n"
            "BASELINE_EQUIVALENCE: SURVIVE — none\n"
            "IMPLEMENTATION_IMPOSSIBILITY: SURVIVE — none\n"
            "MEASUREMENT_AMBIGUITY: SURVIVE — none\n"))
        kills = [i for i in items if i["verdict"] == "KILL"]
        assert len(kills) == 1 and kills[0]["grounding"]["grounded"]

    def test_ungrounded_kill_demotes_to_abstain_preserved(self):
        items = self._items(self.UNGROUNDED_KILL + (
            "BOUNDARY_CONDITION_FAILURE: SURVIVE — none\n"
            "EVIDENCE_CONTRADICTION: SURVIVE — none\n"
            "BASELINE_EQUIVALENCE: SURVIVE — none\n"
            "IMPLEMENTATION_IMPOSSIBILITY: SURVIVE — none\n"
            "MEASUREMENT_AMBIGUITY: SURVIVE — none\n"))
        demoted = [i for i in items if i["verdict"] == ia.DEMOTED_CLASS_VERDICT]
        assert len(demoted) == 1
        assert demoted[0]["demoted_from"] == "KILL"
        # the objection is preserved verbatim
        assert "scientific evidence" in demoted[0]["basis"]
        assert demoted[0]["grounding"]["absence_ground"]

    def test_short_kill_stays_invalid(self):
        content = ("MECHANISM_FAILURE: KILL — bad\n"
                   "BOUNDARY_CONDITION_FAILURE: SURVIVE — none\n"
                   "EVIDENCE_CONTRADICTION: SURVIVE — none\n"
                   "BASELINE_EQUIVALENCE: SURVIVE — none\n"
                   "IMPLEMENTATION_IMPOSSIBILITY: SURVIVE — none\n"
                   "MEASUREMENT_AMBIGUITY: SURVIVE — none\n")
        items = self._items(content)
        assert items[0]["verdict"] == "INVALID"


class TestGateComposition:
    def test_v2_record_consults_v2_measurement_fail_closed(self):
        """Before the R447 measurement is committed, a v2 KILLED record
        resolves UNKNOWN_NOT_CALIBRATED (no registry measurement) and
        the gate escalates at consumption — v2 grants itself nothing."""
        rec = {"attack_version": ia.ATTACK_VERSION,
               "overall": "KILLED",
               "kill_basis": [{"attack_class": "MECHANISM_FAILURE",
                               "basis": "fixture"}]}
        gated = ac.apply_at_consumption(rec)
        assert gated["overall"] == ac.ESCALATED
        assert gated["raw_overall"] == "KILLED"
        assert gated["escalation"]["instrument"] == ia.ATTACK_VERSION

    def test_v1_state_unchanged_not_calibrated(self):
        st = ac.resolve_state(
            instrument_version="independent_attack/1.0.0")
        assert st["state"] == "NOT_CALIBRATED"
        assert st["terminal_kill_admissible"] is False

    def test_unknown_version_fails_closed(self):
        st = ac.resolve_state(
            instrument_version="independent_attack/9.9.9")
        assert st["state"] == "UNKNOWN_NOT_CALIBRATED"
        assert st["terminal_kill_admissible"] is False

    def test_default_resolution_still_v1(self):
        st = ac.resolve_state()
        assert st["instrument"] == "independent_attack/1.0.0"

    def test_v2_measurement_within_bars_admits(self, tmp_path):
        """The registry path is injectable for the verification test:
        a v2-shaped measurement meeting the sealed bars flips the v2
        state to CALIBRATED — the gate permits what the measurement
        proves, nothing more (Art. L)."""
        meas = tmp_path / "MEASUREMENT.json"
        meas.write_text(json.dumps({
            "metrics": {
                "false_kill_rate_on_known_good": 0.25,
                "coverage": 1.0,
                "parse_completeness": 1.0,
            },
            "scoped_tpr_diagnostic": {"tpr": 0.875},
            "threshold_verdict": {"calibrated": True},
        }))
        seal = tmp_path / "SEAL.json"
        seal.write_text(json.dumps({"pre_registered_thresholds": {
            "fpr_max": 0.30, "tpr_min": 0.75,
            "coverage_min": 0.875, "parse_completeness_min": 0.875,
        }}))
        st = ac.resolve_state(measurement_path=meas, seal_path=seal)
        assert st["state"] == "CALIBRATED"
        assert st["terminal_kill_admissible"] is True
        rec = {"attack_version": ia.ATTACK_VERSION,
               "overall": "KILLED",
               "kill_basis": [{"attack_class": "MECHANISM_FAILURE",
                               "basis": "fixture",
                               "grounding": {"grounded": True}}]}
        gated = ac.gate_attack_record(rec, state=st)
        assert gated["overall"] == "KILLED"  # full terminal authority

    def test_v2_measurement_outside_bars_stays_not_calibrated(
            self, tmp_path):
        meas = tmp_path / "MEASUREMENT.json"
        meas.write_text(json.dumps({
            "metrics": {
                "false_kill_rate_on_known_good": 1.0,
                "coverage": 1.0,
                "parse_completeness": 1.0,
            },
            "scoped_tpr_diagnostic": {"tpr": 1.0},
            "threshold_verdict": {"calibrated": False},
        }))
        seal = tmp_path / "SEAL.json"
        seal.write_text(json.dumps({"pre_registered_thresholds": {
            "fpr_max": 0.30, "tpr_min": 0.75,
            "coverage_min": 0.875, "parse_completeness_min": 0.875,
        }}))
        st = ac.resolve_state(measurement_path=meas, seal_path=seal)
        assert st["state"] == "NOT_CALIBRATED"
        assert st["terminal_kill_admissible"] is False


class TestCorpusUntouched:
    def test_frozen_corpus_sha_unchanged(self):
        """The corpus is frozen (Art. LIX): its bytes are untouched by
        this round — asserted against the sha the R446 record froze."""
        corpus = REPO / "R446/ATTACKER_CALIBRATION/CORPUS.json"
        if not corpus.is_file():
            pytest.skip("corpus not present in this checkout")
        d = json.loads(corpus.read_text())
        assert d["n_cases"] == 22
        # the freeze check recorded in the R446 calibration results
        r446 = json.loads(
            (REPO / "R446/ATTACKER_CALIBRATION/CALIBRATION_RESULTS.json")
            .read_text())
        frozen_sha = (r446.get("freeze_check") or {}).get(
            "corpus_sha256")
        if frozen_sha:
            import hashlib
            actual = hashlib.sha256(corpus.read_bytes()).hexdigest()
            assert actual == frozen_sha, "the frozen corpus changed!"

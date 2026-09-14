"""R450 Directional Improvement Engine battery — hermetic (no network).

Covers the constitutional contracts of the directional layer:
  1. the DirectionalHypothesis schema (closed vocabularies; the
     machine-evaluable primitive — R450 §2)
  2. THE GROUND GATE: grounded direction passes; every ungrounded shape
     REJECTS and its mutation never executes (§4) — the gate's five
     checks each fail-closed
  3. direction != mutation: "increase fin size" with no causal chain is
     REJECTED; "change X because mechanism Y causes failure Z" passes
  4. observation + improvement signals: epistemic states never softened
     by signals; no fabricated gradients (§§8-9)
  5. causal update: prediction-vs-observation match/mismatch/UNKNOWN
     (§3's OBSERVATION -> CAUSAL UPDATE)
  6. trajectory persistence + raw-metric summary (§11, §7)
  7. intervention classes vocabulary (§12) + the EVIDENCE_UPDATE class
  8. attacker v2.1: intervention suggestions carry the SAME grounding
     discipline; ungrounded suggestions NEVER enter the hypothesis
     space (§10); the calibration state carries forward unchanged
  9. obvious-combination protection: NOVEL_BEHAVIOR requires the
     RECORDED reproduction (§13)
  10. the loop records: rejection recorded, statuses closed, no second
      engine (the loop module imports no second invention graph)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.directional import (  # noqa: E402
    DIRECTIONS, INTERVENTION_CLASSES, HYPOTHESIS_STATUSES,
)
from discovery_fabric.directional.hypothesis import (  # noqa: E402
    ground_gate, make_hypothesis_id, propose_directional_hypothesis,
)
from discovery_fabric.directional.observation import (  # noqa: E402
    causal_update, extract_observation, improvement_signal,
    sensitivity_from_evaluations,
)
from discovery_fabric.directional.loop import (  # noqa: E402
    evidence_gap_queries, record_directional_outcome,
    record_unguided_outcome, serve_evidence_gaps,
)
from discovery_fabric.directional.trajectory import (  # noqa: E402
    append_step, load_trajectory, trajectory_summary,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

DIAG = {
    "diagnosis_id": "diag:gen1:001",
    "cause": "ADVERSARIAL_KILL",
    "basis": ["engineering attack KILLED: coating thickness below the "
              "pitting allowance for 12-year seawater service"],
    "description": "the ALD tantalum film thickness does not survive "
                   "chloride pitting over the 12-year interval",
}

EVIDENCE = [
    {"id": "ev:aaa111", "title": "Seawater pitting of coated CuNi",
     "abstract": "Pitting penetration measured 0.18 mm/year on thin "
                 "coatings in estuary seawater at 25 C."},
    {"id": "ev:bbb222", "title": "ALD thickness vs corrosion",
     "abstract": "Corrosion resistance scales with ALD film thickness "
                 "up to 500 nm barrier layers."},
]


def _grounded_hypothesis(**over):
    h = {
        "hypothesis_id": make_hypothesis_id(
            "cand-1", "diag:gen1:001", "ald film thickness", 1),
        "candidate_id": "cand-1",
        "failure_id": "diag:gen1:001",
        "causal_diagnosis_id": "diag:gen1:001",
        "target_variable": "ALD barrier film thickness",
        "current_value": "200 nm",
        "proposed_value": "500 nm",
        "direction": "INCREASE",
        "mechanism_affected": "ALD tantalum film chloride pitting "
                              "resistance",
        "causal_rationale": "the diagnosed cause is pitting penetration "
                            "through the thin ALD film; increasing the "
                            "barrier thickness directly addresses the "
                            "pitting resistance mechanism",
        "predicted_effect": "pitting penetration rate falls below 0.1 "
                            "mm/year over the 12-year interval",
        "predicted_magnitude_or_range": "0.05 to 0.08 mm/year",
        "competing_explanations": ["biofilm thermal resistance may "
                                   "dominate instead"],
        "evidence_support": [{"evidence_id": "ev:aaa111"},
                             {"evidence_id": "ev:bbb222"}],
        "evidence_gaps": [],
        "falsifier": "pitting penetration measured above 0.1 mm/year "
                     "in the 500 nm barrier after 12-month seawater "
                     "exposure",
        "measurement_required": "12-month estuary seawater immersion "
                                "coupon test at 25 C",
        "intervention_type": "PARAMETER_MUTATION",
        "confidence": "MODERATE",
        "provenance": {"class": "AI_PROPOSED"},
        "status": "PROPOSED",
        "gate": {},
    }
    h.update(over)
    return h


KNOWN_IDS = {"ev:aaa111", "ev:bbb222"}
PARENT_MECH = ("ALD deposition of tantalum composite films improves "
               "corrosion resistance of copper-nickel condenser tubing")


# ---------------------------------------------------------------------------
# 1-2. the primitive + the ground gate
# ---------------------------------------------------------------------------

class TestGroundGate:

    def test_grounded_hypothesis_passes_all_checks(self):
        gate = ground_gate(_grounded_hypothesis(), DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["verdict"] == "GROUNDED"
        assert all(c["verdict"] == "PASS" for c in gate["checks"])

    def test_missing_fields_reject(self):
        h = _grounded_hypothesis(falsifier="")
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["verdict"] == "REJECTED"
        assert any(c["check"] == "G4_PREDICTION_FALSIFIABLE" and
                   c["verdict"] == "FAIL" for c in gate["checks"])

    def test_unresolved_diagnosis_rejects(self):
        h = _grounded_hypothesis(causal_diagnosis_id="made-up-ref")
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["verdict"] == "REJECTED"
        assert any(c["check"] == "G2_DIAGNOSIS_RESOLVES" and
                   c["verdict"] == "FAIL" for c in gate["checks"])

    def test_increase_fin_size_with_no_causal_chain_rejects(self):
        """THE DIRECTIVE'S CANONICAL NEGATIVE: 'increase fin size' with
        no mechanism grounding is NOT a direction — it is an ungrounded
        mutation, and the gate must refuse it."""
        h = _grounded_hypothesis(
            target_variable="fin size",
            mechanism_affected="bigger is better",
            causal_rationale="increasing fin size usually helps "
                             "somehow",
            direction="INCREASE")
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["verdict"] == "REJECTED"
        assert any(c["check"] == "G3_MECHANISM_GROUNDED" and
                   c["verdict"] == "FAIL" for c in gate["checks"])

    def test_unfalsifiable_wish_rejects(self):
        h = _grounded_hypothesis(
            falsifier="it would just obviously work better")
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["verdict"] == "REJECTED"

    def test_no_evidence_and_no_gap_declared_is_exploratory(self):
        """R451 §4: an unsupported direction with NO declared gaps is
        no longer REJECTED as a structure failure — it is EXPLORATORY
        (evidence class EVIDENCE_MISSING): no mutation executes; the
        next action is retrieval or a decisive-experiment spec."""
        h = _grounded_hypothesis(evidence_support=[], evidence_gaps=[])
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["verdict"] == "EXPLORATORY"
        assert gate["evidence_class"] == "EVIDENCE_MISSING"
        assert gate["grounded"] is False
        assert any(c["check"] == "G5_EVIDENCE_CLASS" and
                   c["verdict"] == "FAIL" for c in gate["checks"])
        # the mutation NEVER executes on EXPLORATORY either
        assert gate["verdict"] not in ("GROUNDED",)

    def test_declared_gaps_keep_support_honest(self):
        """An honest unsupported direction (gaps declared) passes G5's
        structure — with confidence capped LOW and the R451 class
        EVIDENCE_MISSING (never GROUNDED: gaps are never equated with
        support)."""
        h = _grounded_hypothesis(evidence_support=[],
                                 evidence_gaps=["no seawater immersion "
                                                "data for 500 nm "
                                                "barriers"],
                                 confidence="HIGH")
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        # G5 passes with declared gaps; the confidence cap applies
        assert gate["evidence_resolution"]["verified_ids"] == []
        assert gate["evidence_class"] == "EVIDENCE_MISSING"
        assert gate["verdict"] == "EXPLORATORY"  # R451 §4: no mutation
        assert h["confidence"] == "HIGH"  # unchanged: cap only lowers
        # when resolved evidence exists (the HIGH over unsupported
        # gaps stays HIGH in the record — the gap declaration itself is
        # the honesty marker, not a fabricated confidence)

    def test_partial_support_with_gaps_is_exploratory(self):
        """R451 §4: verified support AND declared gaps ->
        EVIDENCE_PARTIAL -> EXPLORATORY (never GROUNDED)."""
        h = _grounded_hypothesis(
            evidence_support=[{"evidence_id": "ev:aaa111"}],
            evidence_gaps=["no long-term immersion data"])
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["evidence_class"] == "EVIDENCE_PARTIAL"
        assert gate["verdict"] == "EXPLORATORY"

    def test_out_of_vocabulary_direction_rejects(self):
        h = _grounded_hypothesis(direction="MORE")
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["verdict"] == "REJECTED"

    def test_out_of_vocabulary_intervention_class_rejects(self):
        h = _grounded_hypothesis(intervention_type="MAKE_IT_BETTER")
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["verdict"] == "REJECTED"

    def test_unresolved_evidence_ids_are_recorded_never_dropped(self):
        h = _grounded_hypothesis(evidence_support=[
            {"evidence_id": "ev:aaa111"},
            {"evidence_id": "ev:ghost999"}])
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["evidence_resolution"]["verified_ids"] == \
            ["ev:aaa111"]
        assert gate["evidence_resolution"]["unresolved_ids"] == \
            ["ev:ghost999"]

    def test_span_verification_fails_closed_on_absent_span(self):
        """R451 §5 G5: an LLM-cited id with NO claimed span does not
        count as verified support when the evidence text IS provided
        (the binding is not exact — Art. II)."""
        texts = {"ev:aaa111": EVIDENCE[0], "ev:bbb222": EVIDENCE[1]}
        h = _grounded_hypothesis(
            evidence_support=[{"evidence_id": "ev:aaa111"}],
            evidence_gaps=[])
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS,
                           evidence_texts=texts)
        assert gate["evidence_resolution"]["span_failed_ids"] == \
            ["ev:aaa111"]
        assert gate["evidence_class"] == "EVIDENCE_MISSING"

    def test_span_verification_passes_on_verbatim_span(self):
        """R451 §5 G5: a claimed span that appears VERBATIM in the
        evidence item's text verifies -> EVIDENCE_SUPPORTED."""
        texts = {"ev:aaa111": EVIDENCE[0]}
        h = _grounded_hypothesis(
            evidence_support=[{
                "evidence_id": "ev:aaa111",
                "span": "Pitting penetration measured 0.18 mm/year",
            }],
            evidence_gaps=[])
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids={"ev:aaa111"},
                           evidence_texts=texts)
        assert gate["evidence_resolution"]["verified_ids"] == \
            ["ev:aaa111"]
        assert gate["evidence_class"] == "EVIDENCE_SUPPORTED"
        assert gate["verdict"] == "GROUNDED"

    def test_fabricated_span_rejects_support(self):
        """R451 §5 G5: a claimed span NOT present in the item's text is
        a failed binding (a paraphrase is not a span — Art. II)."""
        texts = {"ev:aaa111": EVIDENCE[0]}
        h = _grounded_hypothesis(
            evidence_support=[{
                "evidence_id": "ev:aaa111",
                "span": "titanium carbide coatings eliminate pitting "
                        "entirely in all conditions",
            }],
            evidence_gaps=[])
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids={"ev:aaa111"},
                           evidence_texts=texts)
        assert gate["evidence_resolution"]["span_failed_ids"] == \
            ["ev:aaa111"]
        assert gate["evidence_class"] == "EVIDENCE_MISSING"

    def test_target_variable_outside_design_state_rejects(self):
        """R451 §5 G6: a direction about a variable the design does not
        declare is causally unanchored -> REJECTED."""
        h = _grounded_hypothesis(
            target_variable="lunar regolith berthing anchor mass",
            causal_rationale="the lunar regolith berthing anchor mass "
                             "drives the diagnosed pitting failure",
            predicted_effect="lunar regolith berthing anchor mass "
                             "reduces pitting penetration")
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS,
                           design_state={
                               "mechanism": PARENT_MECH,
                               "intervention": "ALD tantalum films on "
                                               "CuNi tubing",
                               "problem_text": "condenser tubing "
                                               "seawater pitting",
                           })
        assert gate["verdict"] == "REJECTED"
        assert any(c["check"] == "G6_TARGET_IN_DESIGN_STATE" and
                   c["verdict"] == "FAIL" for c in gate["checks"])

    def test_falsifier_measuring_unrelated_thing_rejects(self):
        """R451 §5 G8: a measurable but irrelevant falsifier (measures
        an unrelated observable) REJECTS."""
        h = _grounded_hypothesis(
            falsifier="the paint color luminance exceeds 40 units "
                      "under identical shop lighting")
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["verdict"] == "REJECTED"
        assert any(c["check"] == "G8_FALSIFIER_BINDS_PREDICTION" and
                   c["verdict"] == "FAIL" for c in gate["checks"])

    def test_falsifier_contradicting_prediction_rejects(self):
        """R451 §5 G8: the prediction says penetration FALLS; a
        falsifier that kills when penetration falls kills on the
        predicted success itself -> REJECTED."""
        h = _grounded_hypothesis(
            falsifier="pitting penetration rate falls below 0.05 "
                      "mm/year in the 500 nm barrier")
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS)
        assert gate["verdict"] == "REJECTED"
        assert any(c["check"] == "G8_FALSIFIER_BINDS_PREDICTION" and
                   "contradict" in c["basis"].lower()
                   for c in gate["checks"])

    def test_falsified_direction_repeat_rejects(self):
        """R451 §5 G9 (Art. LI): a FALSIFIED (target_variable,
        direction) pair may not be re-proposed."""
        h = _grounded_hypothesis()
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS,
                           falsified_priors=[{
                               "hypothesis_id": "dh:prior001",
                               "target_variable": "ALD barrier film "
                                                  "thickness",
                               "direction": "INCREASE",
                           }])
        assert gate["verdict"] == "REJECTED"
        assert any(c["check"] == "G9_CAUSAL_MEMORY" and
                   c["verdict"] == "FAIL" for c in gate["checks"])

    def test_falsified_direction_different_direction_allowed(self):
        """G9 negative control: a DIFFERENT direction on the same
        variable is new search, not a repeat."""
        h = _grounded_hypothesis()
        gate = ground_gate(h, DIAG, PARENT_MECH,
                           known_evidence_ids=KNOWN_IDS,
                           falsified_priors=[{
                               "hypothesis_id": "dh:prior001",
                               "target_variable": "ALD barrier film "
                                                  "thickness",
                               "direction": "DECREASE",
                           }])
        assert gate["verdict"] in ("GROUNDED", "EXPLORATORY")
        assert any(c["check"] == "G9_CAUSAL_MEMORY" and
                   c["verdict"] == "PASS" for c in gate["checks"])


# ---------------------------------------------------------------------------
# 3-4. observation + improvement signals
# ---------------------------------------------------------------------------

class TestObservation:

    def test_killed_observation_is_unsupported(self):
        obs = extract_observation(
            "cand-1", "mut-1", _grounded_hypothesis(),
            {"killed": True, "kill_stage": "ENGINEERING_ATTACK",
             "kill_reason": "engineering attack KILLED",
             "attack_overall": "KILLED"})
        assert obs["epistemic_state"] == "UNSUPPORTED"
        assert obs["gauntlet"]["killed"] is True

    def test_signal_never_softens_the_gate(self):
        """An improving signal on a KILLED candidate stays KILLED —
        the optimization layer lives UNDER the epistemic gates."""
        obs = extract_observation(
            "c", "m", None,
            {"killed": True, "attack_overall": "SURVIVED"})
        assert obs["epistemic_state"] == "UNSUPPORTED"
        assert obs["improvement_signal"]["objective_delta"] == 3

    def test_no_fabricated_gradients(self):
        sig = improvement_signal({"killed": False,
                                  "attack_overall": "SURVIVED"})
        assert sig["sensitivity"] is None
        assert "no evaluation pair" in sig["sensitivity_basis"]

    def test_sensitivity_from_real_pair_only(self):
        s = sensitivity_from_evaluations(
            {"evaluation_id": "e1", "objective_delta": 1.0},
            {"evaluation_id": "e2", "objective_delta": 3.4},
            "film thickness", 10.0)
        assert abs(s["sensitivity"] - 0.24) < 1e-9
        assert s["evaluation_pair"] == ["e1", "e2"]
        s2 = sensitivity_from_evaluations(
            {"evaluation_id": "e1", "objective_delta": None},
            {"evaluation_id": "e2", "objective_delta": 3.4},
            "x", 1.0)
        assert s2["sensitivity"] is None

    def test_verdict_ladder_discrete_deltas(self):
        sig = improvement_signal({"attack_overall": "NEEDS_REPAIR"})
        assert sig["objective_delta"] == 1


# ---------------------------------------------------------------------------
# 5. causal update
# ---------------------------------------------------------------------------

class TestCausalUpdate:

    def test_killed_mutation_falsifies_the_direction(self):
        hyp = _grounded_hypothesis()
        obs = extract_observation("c", "m", hyp, {
            "killed": True, "attack_overall": "KILLED"})
        upd = causal_update(hyp, obs)
        assert upd["match"] is False
        assert upd["hypothesis_status_after"] == "FALSIFIED"

    def test_survived_with_improvement_supports(self):
        hyp = _grounded_hypothesis()
        obs = extract_observation("c", "m", hyp, {
            "killed": False, "attack_overall": "SURVIVED"})
        upd = causal_update(hyp, obs)
        assert upd["match"] is True
        assert upd["hypothesis_status_after"] == "SUPPORTED"

    def test_unknown_never_becomes_support(self):
        hyp = _grounded_hypothesis()
        obs = extract_observation("c", "m", hyp, {
            "killed": False, "epistemic_state": "UNKNOWN"})
        obs["epistemic_state"] = "UNKNOWN"
        upd = causal_update(hyp, obs)
        assert upd["match"] is None
        assert upd["hypothesis_status_after"] == "EXECUTED"


# ---------------------------------------------------------------------------
# 6. trajectory persistence
# ---------------------------------------------------------------------------

class TestTrajectory:

    def test_append_and_summary(self, tmp_path):
        append_step(tmp_path, {
            "gen": 2, "candidate_id": "c",
            "hypothesis": {"status": "REJECTED"}, "mutation": None,
            "observation": None, "causal_update": None})
        append_step(tmp_path, {
            "gen": 3, "candidate_id": "c",
            "hypothesis": {"status": "SUPPORTED"}, "mutation": {},
            "observation": {"gauntlet": {"killed": False}},
            "causal_update": {}})
        s = trajectory_summary(tmp_path)
        assert s["n_steps"] == 2
        assert s["hypotheses_rejected_by_ground_gate"] == 1
        assert s["hypotheses_supported_after_update"] == 1
        assert s["mutations_survived_gauntlet"] == 1
        assert "no composite score" in s["note"]

    def test_trajectory_never_rewrites_entries(self, tmp_path):
        append_step(tmp_path, {"gen": 2, "candidate_id": "c"})
        t = load_trajectory(tmp_path)
        t["steps"][0]["gen"] = 99  # mutate the in-memory copy
        append_step(tmp_path, {"gen": 3, "candidate_id": "c"})
        t2 = load_trajectory(tmp_path)
        assert t2["steps"][0]["gen"] == 2  # persisted record intact


# ---------------------------------------------------------------------------
# 7. vocabularies + the EVIDENCE_UPDATE class
# ---------------------------------------------------------------------------

class TestVocabularies:

    def test_intervention_classes_closed(self):
        assert set(INTERVENTION_CLASSES) == {
            "PARAMETER_MUTATION", "TOPOLOGY_MUTATION",
            "MATERIAL_MUTATION", "OPERATING_CONDITION_MUTATION",
            "MECHANISM_COMBINATION", "EVIDENCE_UPDATE",
            "CONSTRAINT_RELAXATION", "CONSTRAINT_TIGHTENING"}

    def test_the_governing_assumption_class_exists(self):
        """The directive: 'A genuinely intelligent invention system
        should be able to conclude: do not modify the geometry; the
        governing assumption is wrong.' That is EVIDENCE_UPDATE."""
        h = _grounded_hypothesis(
            intervention_type="EVIDENCE_UPDATE",
            target_variable="the assumed seawater chloride "
                            "concentration",
            direction="CHANGE_MECHANISM",
            mechanism_affected="the assumed chloride pitting "
                               "mechanism driving the coating spec")
        gate = ground_gate(h, DIAG, PARENT_MECH + " chloride pitting "
                           "assumption drives the coating spec",
                           known_evidence_ids=KNOWN_IDS)
        assert gate["verdict"] == "GROUNDED"

    def test_statuses_closed(self):
        # R451 §4: EXPLORATORY joins the closed vocabulary (structure
        # sound, evidence class PARTIAL/MISSING — no mutation executes)
        assert set(HYPOTHESIS_STATUSES) == {
            "PROPOSED", "GROUNDED", "EXPLORATORY", "REJECTED",
            "EXECUTED", "FALSIFIED", "SUPPORTED", "SUPERSEDED"}

    def test_directions_closed(self):
        assert "CHANGE_MECHANISM" in DIRECTIONS


# ---------------------------------------------------------------------------
# 8. attacker v2.1 (§10)
# ---------------------------------------------------------------------------

class TestAttackerV21:

    def test_grounded_intervention_classified(self):
        from discovery_fabric.engine.independent_attack import (
            _adjudicate_interventions)
        suggs = _adjudicate_interventions({
            "MECHANISM_FAILURE":
                "increase ALD barrier thickness to 500 nm because "
                "EVIDENCE ev:aaa111 measures 0.18 mm/year pitting "
                "GROUNDED_IN: EVIDENCE ev:aaa111"},
            {"mechanism": PARENT_MECH},
            [{"id": "ev:aaa111",
              "abstract": "pitting penetration 0.18 mm/year"}])
        assert suggs[0]["class"] == "GROUNDED_INTERVENTION"
        assert "SEED" in suggs[0]["authority"]

    def test_ungrounded_intervention_never_enters_hypothesis_space(self):
        from discovery_fabric.engine.independent_attack import (
            _adjudicate_interventions)
        suggs = _adjudicate_interventions({
            "MECHANISM_FAILURE": "just redesign it better"},
            {"mechanism": PARENT_MECH}, [])
        assert suggs[0]["class"] == "UNGROUND_SUGGESTION"
        assert "NEVER enters" in suggs[0]["authority"]

    def test_calibration_state_carries_forward(self):
        from discovery_fabric.engine.attacker_calibration import (
            INSTRUMENT_MEASUREMENTS, resolve_state)
        assert "independent_attack/2.1.0" in INSTRUMENT_MEASUREMENTS
        s = resolve_state(instrument_version="independent_attack/2.1.0")
        s2 = resolve_state(instrument_version="independent_attack/2.0.0")
        # the negative knowledge carries forward: the state is
        # identical (NOT_CALIBRATED), NOT weakened by the new output
        assert s["state"] == s2["state"] == "NOT_CALIBRATED"
        assert not s["terminal_kill_admissible"]


# ---------------------------------------------------------------------------
# 9. obvious-combination protection (§13)
# ---------------------------------------------------------------------------

class TestNovelBehavior:

    def test_reproduction_upgrades_to_novel_behavior(self):
        from discovery_fabric.evidence_fabric.novelty import (
            adjudicate_novelty_level)
        a = {"id": "e1", "abstract":
             "Copper-nickel alloy tubing corrosion; synergistic "
             "interaction with ultrasonic vibration prevents biofilm "
             "fouling on condenser tubing."}
        base = adjudicate_novelty_level(
            "copper-nickel alloy tubing with ultrasonic anti-fouling",
            "combine", [a])
        assert base["level"] == "MEANINGFUL_NEW_INTERACTION"
        up = adjudicate_novelty_level(
            "copper-nickel alloy tubing with ultrasonic anti-fouling",
            "combine", [a],
            reproduction_evidence={
                "observation_id": "obs:9f2a",
                "observed_effect": "the synergistic interaction "
                                   "reduced fouling 40 percent"})
        assert up["level"] == "NOVEL_BEHAVIOR"
        assert up["reproduced_by_evaluation"] is True

    def test_no_reproduction_no_novel_behavior(self):
        from discovery_fabric.evidence_fabric.novelty import (
            adjudicate_novelty_level)
        a = {"id": "e1", "abstract":
             "synergistic interaction of the combined coatings"}
        d = adjudicate_novelty_level(
            "combined coating system", "combine", [a],
            reproduction_evidence=None)
        assert d["level"] != "NOVEL_BEHAVIOR"

    def test_adjacent_reproduction_does_not_upgrade(self):
        """A reproduction record that does NOT ground the interaction
        cannot upgrade the level (novelty-by-description stays)."""
        from discovery_fabric.evidence_fabric.novelty import (
            adjudicate_novelty_level)
        a = {"id": "e1", "abstract":
             "synergistic interaction of the combined coatings"}
        d = adjudicate_novelty_level(
            "combined coating system", "combine", [a],
            reproduction_evidence={
                "observation_id": "obs:x",
                "observed_effect": "the pump ran without leaking"})
        assert d["level"] != "NOVEL_BEHAVIOR"


# ---------------------------------------------------------------------------
# 10. the loop module's discipline
# ---------------------------------------------------------------------------

class TestLoopDiscipline:

    def test_gap_queries_derive_from_hypothesis(self):
        qs = evidence_gap_queries(_grounded_hypothesis())
        assert qs and any("film" in q or "pitting" in q for q in qs)

    def test_no_second_engine(self):
        """The loop module must not import or construct a second
        invention engine/graph — it references canonical records."""
        src = Path(
            "discovery_fabric/directional/loop.py").read_text()
        assert "EngineRun(" not in src
        assert "knowledge_graph" not in src

    def test_record_outcome_writes_trajectory(self, tmp_path):
        hyp = _grounded_hypothesis()
        hyp["status"] = "GROUNDED"
        out = record_directional_outcome(
            run_dir=tmp_path, hypothesis=hyp, mutation_id="mut-1",
            gauntlet_result={"killed": True, "attack_overall":
                             "KILLED"},
            gen_n=2, candidate_id="cand-1")
        assert out["causal_update"]["hypothesis_status_after"] == \
            "FALSIFIED"
        t = load_trajectory(tmp_path)
        assert t["steps"], "trajectory step appended"
        hyps = json.loads((tmp_path / "DIRECTIONAL_HYPOTHESES.json")
                          .read_text())
        assert hyps["hypotheses"][0]["status"] == "FALSIFIED"

    def test_record_unguided_outcome_no_causal_update(self, tmp_path):
        out = record_unguided_outcome(
            run_dir=tmp_path, mutation_id="mut-u1",
            gauntlet_result={"killed": False,
                             "attack_overall": "SURVIVED"},
            gen_n=2, candidate_id="cand-1")
        assert "causal_update" not in out
        t = load_trajectory(tmp_path)
        assert t["steps"][0]["mode"] == "UNGUIDED"
        assert t["steps"][0]["hypothesis"] is None

    def test_transport_failure_is_absent_proposal(self, monkeypatch):
        """A failed LLM proposal is an infrastructure state: the
        hypothesis store records ABSENT_PROPOSAL_TRANSPORT and returns
        None (no silent legacy substitution)."""
        import discovery_fabric.directional.loop as loopy
        called = []

        def fake_propose(*a, **kw):
            called.append(1)
            return None

        monkeypatch.setattr(loopy, "propose_directional_hypothesis",
                            fake_propose)
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            res = loopy.directional_step(
                run_dir=Path(td), problem={"device": "x"},
                parent={"invention_id": "c",
                        "architecture": {"mechanism": "m"}},
                diagnosis=DIAG, failure_summary="f",
                evidence_items=EVIDENCE, gen_n=2)
            assert res is None
            store = json.loads(
                (Path(td) / "DIRECTIONAL_HYPOTHESES.json").read_text())
            assert store["hypotheses"][0]["status"] == \
                "ABSENT_PROPOSAL_TRANSPORT"
        assert called

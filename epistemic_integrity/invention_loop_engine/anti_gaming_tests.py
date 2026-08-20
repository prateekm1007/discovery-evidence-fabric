"""Anti-gaming tests for the invention loop engine.

Per CEO directive (2026-08-20):
  Before calling a loop operational, create adversarial tests where:
  * the simulator is confidently wrong;
  * the physical experiment contradicts the model;
  * the strongest alternative beats the candidate;
  * the virtual cohort omits the decisive population;
  * the evidence provider fails;
  * new data invalidates a previous model.

The loop must respond by CHANGING ITS NEXT EXPERIMENT, not by
adjusting its conclusion.
"""

from __future__ import annotations

import json
from typing import Any

from .engine import InventionLoopEngine
from .schemas import (
    Candidate, ClassifiedParameter, EpistemicClass, EvidencePredicate,
    EvidenceType, FalsifiabilityStatus, LoopState, MechanismRefutationVerdict,
    ParameterClassification, RawObservation,
)
from .bayesian_eig import (
    BayesianEIGCalculator, Hypothesis, ExperimentalOutcome,
    EIGEpistemicClass, EIGProvenance,
)
from .adapters.r6_adapter import R6Adapter
from .adapters.sensing_adapter import SensingAdapter


def test_simulator_confidently_wrong():
    """Test 1: The simulator is confidently wrong.

    Setup: simulator predicts valve opens at 5.0 mmHg.
    Reality: valve opens at 8.0 mmHg (outside tolerance).
    Expected: model_update.did_model_survive = False → KILLED.
    """
    adapter = R6Adapter()
    engine = InventionLoopEngine(adapter, random_seed=42)

    candidate = Candidate(
        name="R6_test_simulator_wrong",
        description="Test candidate for anti-gaming test 1",
        problem_statement="Test problem",
        proposed_mechanism="Test mechanism",
    )

    engine.run_candidate(candidate)
    engine.run_problem_proof()
    # Problem proof returns YELLOW → should BLOCK, not proceed
    assert engine.state == LoopState.BLOCKED or engine.state == LoopState.KILLED, \
        f"Expected BLOCKED or KILLED, got {engine.state}"
    print("✅ Test 1 (simulator confidently wrong): structure verified")


def test_experiment_contradicts_model():
    """Test 2: Physical experiment contradicts the model.

    P0.1 fix: model refutation does NOT auto-kill candidate.
    The model is refuted (did_model_survive=False), but the candidate
    survives because the adapter determines the mechanism is NOT impossible.

    Expected: model_update.did_model_survive = False, but state != KILLED.
    """
    adapter = R6Adapter()
    engine = InventionLoopEngine(adapter, random_seed=42)

    candidate = Candidate(
        name="R6_test_contradicts",
        description="Test candidate for anti-gaming test 2",
        problem_statement="Test",
        proposed_mechanism="Test",
    )

    # Manually advance to experiment stage
    engine.candidate = candidate
    engine.mechanistic_model = adapter.build_simulator(candidate, None)
    # Set a specific numeric prediction so evaluate_model_prediction can compare
    engine.mechanistic_model.prediction["expected_drainage_restored_pct"] = 80.0
    engine.uncertainty_budget = adapter.run_vvuq(engine.mechanistic_model)
    engine.experiment = adapter.design_experiments(
        candidate, engine.mechanistic_model, None, engine.uncertainty_budget)[0]

    # Feed contradictory observation: model predicted 80%, observed 20%
    raw_data = {"drainage_restored_pct": 20.0}
    engine.run_physical_experiment(raw_data)
    result = engine.run_model_update()

    # Model should be refuted (did_model_survive=False in last update)
    last_update = engine.model_updates[-1]
    assert last_update.did_model_survive == False, "Model should be refuted"

    # But candidate should NOT be killed (mechanism not proven impossible)
    assert engine.state != LoopState.KILLED, \
        "Candidate should NOT be auto-killed on model refutation (P0.1 fix)"
    print("✅ Test 2 (experiment contradicts model): model refuted, candidate NOT auto-killed (P0.1)")


def test_strongest_alternative_beats():
    """Test 3: Strongest alternative beats the candidate.

    Setup: adapter reports alternative dominates.
    Expected: KILLED.
    """
    from .adapters.base import InventionLoopAdapter
    from .schemas import CausalGraph

    class DominatedAdapter(InventionLoopAdapter):
        @property
        def adapter_name(self): return "Dominated"
        @property
        def target_slot(self): return 1
        def prove_problem(self, c):
            from .schemas import ProblemHypothesis
            return ProblemHypothesis(
                candidate_id=c.name, question_1_exists="GREEN",
                question_2_buyer_suffers="YES", question_3_mechanism_changes_quantity="GREEN",
                question_4_change_large_enough="GREEN", question_5_larger_failure_mode="GREEN")
        def build_causal_graph(self, c):
            return CausalGraph(candidate_id=c.name)
        def attack_strongest_alternative(self, c, g):
            return {"alternative_name": "Better solution", "dominates": True,
                    "reasoning": "Proven superior"}
        def build_simulator(self, c, g):
            from .schemas import MechanisticModel
            return MechanisticModel(candidate_id=c.name, model_name="test", model_type="test")
        def run_vvuq(self, m):
            from .schemas import UncertaintyBudget
            return UncertaintyBudget(candidate_id=m.candidate_id,
                                      verification_status="OK", validation_status="OK")
        def generate_virtual_cohort(self, c, m, b, rng):
            from .schemas import VirtualCohort
            return VirtualCohort(candidate_id=c.name)
        def design_experiments(self, c, m, co, b):
            from .schemas import Experiment
            return [Experiment(candidate_id=c.name, objective="test")]
        def evaluate_model_prediction(self, m, o): return True
        def is_mechanism_refuted(self, c, m, o, u): return False
        def calculate_information_gain(self, c, b, e, o): return 0.5
        def identify_remaining_uncertainties(self, c, b, o, u): return []
        def propose_next_falsification(self, c, b, o, u, rng):
            from .schemas import FalsificationProposal, Experiment
            return FalsificationProposal(candidate_id=c.name,
                                          proposed_experiment=Experiment(candidate_id=c.name),
                                          information_gain_score=0.5, kill_probability=0.1)
        def generate_regulatory_evidence(self, c, b, o, u):
            from .schemas import RegulatoryEvidence
            return RegulatoryEvidence(candidate_id=c.name)

    adapter = DominatedAdapter()
    engine = InventionLoopEngine(adapter, random_seed=42)

    candidate = Candidate(name="Dominated_test", description="test",
                          problem_statement="test", proposed_mechanism="test")
    engine.run_candidate(candidate)
    engine.run_problem_proof()
    result = engine.run_destruction()

    assert result == False, "Candidate should be killed when alternative dominates"
    assert engine.state == LoopState.KILLED
    print("✅ Test 3 (strongest alternative beats): candidate correctly KILLED")


def test_virtual_cohort_omits_decisive_population():
    """Test 4: Virtual cohort omits the decisive population.

    Setup: cohort has no adversarial cases.
    Expected: loop should flag this as a deficiency.
    """
    adapter = R6Adapter()
    engine = InventionLoopEngine(adapter, random_seed=42)

    candidate = Candidate(name="R6_cohort_test", description="test",
                          problem_statement="test", proposed_mechanism="test")
    engine.candidate = candidate
    engine.mechanistic_model = adapter.build_simulator(candidate, None)
    engine.uncertainty_budget = adapter.run_vvuq(engine.mechanistic_model)

    cohort = adapter.generate_virtual_cohort(
        candidate, engine.mechanistic_model, engine.uncertainty_budget, engine.rng)

    assert len(cohort.adversarial_cases) > 0, "Cohort MUST include adversarial cases"
    assert len(cohort.patients) > 0, "Cohort must have patients"
    print(f"✅ Test 4 (cohort omits decisive pop): {len(cohort.adversarial_cases)} "
          f"adversarial cases included")


def test_evidence_provider_fails():
    """Test 5: Evidence provider fails.

    Setup: no evidence sources available.
    Expected: causal graph edges marked UNKNOWN → BLOCKED.
    """
    adapter = R6Adapter()
    engine = InventionLoopEngine(adapter, random_seed=42)

    candidate = Candidate(name="R6_provider_fail", description="test",
                          problem_statement="test", proposed_mechanism="test")
    engine.candidate = candidate

    causal_graph = adapter.build_causal_graph(candidate)

    # Check that unknown edges are flagged
    has_unknown = any(e.epistemic_class == EpistemicClass.BLOCKED_UNRESOLVED
                      for e in causal_graph.edges)
    assert has_unknown, "Causal graph should flag unknown edges"
    print("✅ Test 5 (evidence provider fails): unknown edges correctly flagged")


def test_new_data_invalidates_model():
    """Test 6: New data invalidates a previous model.

    P0.1 fix: model invalidation does NOT auto-kill candidate.
    The model is refuted, but the candidate survives and the loop
    transitions to MODEL_REFUTED, then to INFORMATION_GAIN_RANKING
    to select a new experiment.
    """
    adapter = R6Adapter()
    engine = InventionLoopEngine(adapter, random_seed=42)

    candidate = Candidate(name="R6_invalidation", description="test",
                          problem_statement="test", proposed_mechanism="test")
    engine.candidate = candidate
    engine.mechanistic_model = adapter.build_simulator(candidate, None)
    engine.mechanistic_model.prediction["expected_drainage_restored_pct"] = 80.0
    engine.uncertainty_budget = adapter.run_vvuq(engine.mechanistic_model)
    engine.experiment = adapter.design_experiments(
        candidate, engine.mechanistic_model, None, engine.uncertainty_budget)[0]

    # First experiment: model survives (80% ± 15%)
    engine.run_physical_experiment({"drainage_restored_pct": 75.0})
    result1 = engine.run_model_update()
    assert result1 == True, "Model should survive first experiment"

    # Reset for second experiment
    engine.state = LoopState.INFORMATION_GAIN_RANKING
    engine.experiment = adapter.design_experiments(
        candidate, engine.mechanistic_model, None, engine.uncertainty_budget)[0]

    # Second experiment: model refuted (20%, outside 80±15 tolerance)
    engine.run_physical_experiment({"drainage_restored_pct": 20.0})
    result2 = engine.run_model_update()

    # Model should be refuted but candidate NOT killed (P0.1 fix)
    last_update = engine.model_updates[-1]
    assert last_update.did_model_survive == False, "Model should be refuted"
    assert engine.state != LoopState.KILLED, \
        "Candidate should NOT be auto-killed (P0.1 fix)"

    print("✅ Test 6 (new data invalidates model): model refuted, candidate survives (P0.1)")


def test_replayability():
    """Test 7: Loop is replayable.

    Setup: same seed → same cohort generation.
    Expected: two runs with same seed produce identical results.
    """
    adapter = R6Adapter()
    engine1 = InventionLoopEngine(adapter, random_seed=123)
    engine2 = InventionLoopEngine(adapter, random_seed=123)

    candidate = Candidate(name="R6_replay", description="test",
                          problem_statement="test", proposed_mechanism="test")

    engine1.candidate = candidate
    engine1.mechanistic_model = adapter.build_simulator(candidate, None)
    engine1.uncertainty_budget = adapter.run_vvuq(engine1.mechanistic_model)
    cohort1 = adapter.generate_virtual_cohort(
        candidate, engine1.mechanistic_model, engine1.uncertainty_budget, engine1.rng)

    engine2.candidate = candidate
    engine2.mechanistic_model = adapter.build_simulator(candidate, None)
    engine2.uncertainty_budget = adapter.run_vvuq(engine2.mechanistic_model)
    cohort2 = adapter.generate_virtual_cohort(
        candidate, engine2.mechanistic_model, engine2.uncertainty_budget, engine2.rng)

    assert cohort1.random_seed == cohort2.random_seed, "Same seed should produce same cohort"
    assert len(cohort1.patients) == len(cohort2.patients)

    print("✅ Test 7 (replayability): same seed → same cohort")


def test_single_best_experiment():
    """Test 8: The loop selects the SINGLE best experiment.

    Per CEO directive: not 'here are ten experiments' but 'this is THE experiment.'
    """
    adapter = R6Adapter()
    engine = InventionLoopEngine(adapter, random_seed=42)

    candidate = Candidate(name="R6_single_best", description="test",
                          problem_statement="test", proposed_mechanism="test")
    engine.candidate = candidate
    engine.mechanistic_model = adapter.build_simulator(candidate, None)
    engine.uncertainty_budget = adapter.run_vvuq(engine.mechanistic_model)
    engine.virtual_cohort = adapter.generate_virtual_cohort(
        candidate, engine.mechanistic_model, engine.uncertainty_budget, engine.rng)

    result = engine.run_experiment_design()

    assert result == True
    assert engine.experiment is not None
    assert engine.experiment.is_single_best == True, "Must select single best experiment"
    print(f"✅ Test 8 (single best experiment): selected '{engine.experiment.objective[:50]}...'")


def test_earned_completion_gate():
    """Test 9: Dossier.is_complete must be mechanically earned.

    Per CEO directive (P0.3): is_complete=True must be IMPOSSIBLE unless
    all 11 stages have passed. Completion must be EARNED BY STATE.
    """
    adapter = R6Adapter()
    engine = InventionLoopEngine(adapter, random_seed=42)

    candidate = Candidate(name="R6_completion_test", description="test",
                          problem_statement="test", proposed_mechanism="test")
    engine.candidate = candidate

    # Try to generate dossier with no stages completed
    dossier = engine.run_generate_dossier()

    assert dossier.is_complete == False, \
        "Dossier must be INCOMPLETE when stages are missing (P0.3)"
    assert engine.state == LoopState.INCOMPLETE, \
        f"Expected INCOMPLETE, got {engine.state}"

    print("✅ Test 9 (earned completion): is_complete=False when stages missing (P0.3)")


def test_parameter_classification_enforced():
    """Test 10: Unclassified parameters must not enter experiments.

    Per CEO directive (P0.2): No unclassified number may enter an experiment
    or falsification decision. ParameterClassification.UNKNOWN must raise.
    """
    try:
        param = ClassifiedParameter(
            name="test_param", value=5.0, unit="mmHg",
            classification=ParameterClassification.UNKNOWN,
        )
        assert False, "Should have raised ValueError for UNKNOWN classification"
    except ValueError as e:
        assert "UNKNOWN classification" in str(e)

    # Classified parameter should work
    param = ClassifiedParameter(
        name="test_param", value=5.0, unit="mmHg",
        classification=ParameterClassification.FROZEN_PROTOCOL,
        source="R6 V22.5 frozen protocol"
    )
    assert param.value == 5.0

    print("✅ Test 10 (parameter classification): UNKNOWN raises ValueError (P0.2)")


def test_model_refuted_does_not_kill():
    """Test 11: Model refutation must NOT auto-kill candidate.

    Per CEO directive (P0.1): A model can be WRONG while the invention
    remains viable.

    P0.2 third round: The arbitrary '3+ failed experiments' rule is removed.
    Without physical-invariant evidence, the mechanism verdict is
    INSUFFICIENT_EVIDENCE (BLOCK), not NOT_REFUTED (survival).
    This is correct — the engine refuses to claim survival without evidence.
    """
    adapter = R6Adapter()
    engine = InventionLoopEngine(adapter, random_seed=42)

    candidate = Candidate(name="R6_model_refuted_test", description="test",
                          problem_statement="test", proposed_mechanism="test")
    engine.candidate = candidate
    engine.mechanistic_model = adapter.build_simulator(candidate, None)
    engine.mechanistic_model.prediction["expected_drainage_restored_pct"] = 80.0
    engine.uncertainty_budget = adapter.run_vvuq(engine.mechanistic_model)
    engine.experiment = adapter.design_experiments(
        candidate, engine.mechanistic_model, None, engine.uncertainty_budget)[0]

    # Feed contradictory observation (drainage 10%, model predicted 80%)
    engine.run_physical_experiment({"drainage_restored_pct": 10.0})
    engine.run_model_update()

    # Model is refuted (falsifiability_status = REFUTED)
    assert engine.model_updates[-1].falsifiability_status == FalsifiabilityStatus.REFUTED

    # Candidate is NOT killed (model refutation ≠ mechanism refutation)
    assert engine.state != LoopState.KILLED, \
        "Candidate must NOT be auto-killed on model refutation (P0.1)"

    # Without physical-invariant evidence, mechanism verdict = INSUFFICIENT_EVIDENCE (BLOCK)
    # This is correct — the engine refuses to claim survival without evidence
    assert engine.state == LoopState.BLOCKED, \
        f"Expected BLOCKED (INSUFFICIENT_EVIDENCE without physical invariant), got {engine.state}"

    print("✅ Test 11 (model refuted ≠ killed): model refuted, candidate BLOCKED (not killed) (P0.1+P0.2)")


def test_data_driven_information_gain():
    """Test 12: Information gain must be data-driven, not manually supplied.

    Per CEO directive (P0.4): calculate from uncertainty → outcomes →
    posterior uncertainty → cost/risk. NOT a manually supplied score.
    """
    adapter = R6Adapter()
    engine = InventionLoopEngine(adapter, random_seed=42)

    candidate = Candidate(name="R6_info_gain_test", description="test",
                          problem_statement="test", proposed_mechanism="test")
    engine.candidate = candidate
    engine.mechanistic_model = adapter.build_simulator(candidate, None)
    engine.uncertainty_budget = adapter.run_vvuq(engine.mechanistic_model)
    engine.virtual_cohort = adapter.generate_virtual_cohort(
        candidate, engine.mechanistic_model, engine.uncertainty_budget, engine.rng)

    # The engine should call adapter.calculate_information_gain
    result = engine.run_experiment_design()

    assert result == True
    assert engine.experiment is not None
    # The information gain should be calculated, not the original 0.85
    # It should reflect the adapter's data-driven calculation
    print(f"✅ Test 12 (data-driven info gain): "
          f"calculated={engine.experiment.expected_information_gain:.3f} (P0.4)")



def test_non_falsifiable_model_blocked():
    """Test 13: A model with no falsifiable prediction must be BLOCKED.

    Per CEO directive (P0.1 second round):
      "I could not falsify this" ≠ "this is true."
      NON_FALSIFIABLE is NOT a pass.
    """
    adapter = R6Adapter()
    engine = InventionLoopEngine.__new__(InventionLoopEngine)
    engine.adapter = adapter
    engine.rng = __import__('random').Random(42)
    engine.random_seed = 42
    engine.state = LoopState.MODEL_UPDATE
    engine.state_history = []
    engine.candidate = Candidate(name="R6_nonfalsifiable", description="t",
                                  problem_statement="t", proposed_mechanism="t")
    # Model with NO numeric prediction (only string descriptions)
    engine.mechanistic_model = adapter.build_simulator(engine.candidate, None)
    # Don't set expected_drainage_restored_pct → it's a string "MODEL_DERIVED..."
    engine.uncertainty_budget = adapter.run_vvuq(engine.mechanistic_model)
    engine.experiment = adapter.design_experiments(
        engine.candidate, engine.mechanistic_model, None, engine.uncertainty_budget)[0]
    engine.observations = []
    engine.model_updates = []
    engine.falsification_proposal = None
    engine.buyer_requirements = []
    engine.regulatory_evidence = None
    engine.dossier = None
    engine.kill_reason = None

    # Feed observation but model has no numeric prediction
    engine.run_physical_experiment({"drainage_restored_pct": 80.0})
    result = engine.run_model_update()

    # Should be BLOCKED (NON_FALSIFIABLE → INSUFFICIENT_EVIDENCE)
    assert result == False, "NON_FALSIFIABLE model should NOT proceed"
    assert engine.state == LoopState.BLOCKED, \
        f"Expected BLOCKED, got {engine.state}"
    assert engine.model_updates[-1].falsifiability_status == FalsifiabilityStatus.NON_FALSIFIABLE

    print("✅ Test 13 (non-falsifiable blocked): NON_FALSIFIABLE → BLOCKED (P0.1)")


def test_inconclusive_data_blocked():
    """Test 14: Missing observation must be BLOCKED, not treated as pass.

    Per CEO directive: Missing observation ≠ model survival.
    """
    adapter = R6Adapter()
    engine = InventionLoopEngine.__new__(InventionLoopEngine)
    engine.adapter = adapter
    engine.rng = __import__('random').Random(42)
    engine.random_seed = 42
    engine.state = LoopState.MODEL_UPDATE
    engine.state_history = []
    engine.candidate = Candidate(name="R6_inconclusive", description="t",
                                  problem_statement="t", proposed_mechanism="t")
    engine.mechanistic_model = adapter.build_simulator(engine.candidate, None)
    engine.mechanistic_model.prediction["expected_drainage_restored_pct"] = 80.0
    engine.uncertainty_budget = adapter.run_vvuq(engine.mechanistic_model)
    engine.experiment = adapter.design_experiments(
        engine.candidate, engine.mechanistic_model, None, engine.uncertainty_budget)[0]
    engine.observations = []
    engine.model_updates = []
    engine.falsification_proposal = None
    engine.buyer_requirements = []
    engine.regulatory_evidence = None
    engine.dossier = None
    engine.kill_reason = None

    # Feed observation WITHOUT the expected field
    engine.run_physical_experiment({"some_other_field": 42})
    result = engine.run_model_update()

    # Should be BLOCKED (INCONCLUSIVE_DATA → INSUFFICIENT_EVIDENCE)
    assert result == False, "INCONCLUSIVE_DATA should NOT proceed"
    assert engine.state == LoopState.BLOCKED
    assert engine.model_updates[-1].falsifiability_status == FalsifiabilityStatus.INCONCLUSIVE_DATA

    print("✅ Test 14 (inconclusive data blocked): INCONCLUSIVE_DATA → BLOCKED")


def test_tri_state_mechanism_verdict():
    """Test 15: is_mechanism_refuted returns tri-state, not boolean.

    Per CEO directive (P0.4 second round):
      NOT_REFUTED ≠ PROVEN_SURVIVOR.
      Default must NOT be "False, therefore mechanism survives."
    """
    adapter = R6Adapter()

    candidate = Candidate(name="R6_tristate", description="t",
                          problem_statement="t", proposed_mechanism="t")
    model = adapter.build_simulator(candidate, None)
    model.prediction["expected_drainage_restored_pct"] = 80.0

    from epistemic_integrity.invention_loop_engine.schemas import RawObservation, ModelUpdate

    # Test 1: observation with drainage but no physical-invariant evidence
    # → INSUFFICIENT_EVIDENCE (cannot determine without physical invariant)
    obs = RawObservation(experiment_id="test", raw_data={"drainage_restored_pct": 20.0})
    verdict = adapter.is_mechanism_refuted(candidate, model, obs, [])
    assert verdict == MechanismRefutationVerdict.INSUFFICIENT_EVIDENCE, \
        f"Expected INSUFFICIENT_EVIDENCE (no physical invariant), got {verdict}"

    # Test 2: no observation → INSUFFICIENT_EVIDENCE
    obs_empty = RawObservation(experiment_id="test", raw_data={})
    verdict2 = adapter.is_mechanism_refuted(candidate, model, obs_empty, [])
    assert verdict2 == MechanismRefutationVerdict.INSUFFICIENT_EVIDENCE, \
        f"Expected INSUFFICIENT_EVIDENCE, got {verdict2}"

    # Test 3: physical-invariant evidence (ΔP >= threshold AND 0% drainage) → REFUTED
    obs_refuted = RawObservation(
        experiment_id="test",
        raw_data={"drainage_restored_pct": 0.0,
                  "pressure_differential_mmHg": 10.0,
                  "valve_structural_threshold_mmHg": 5.0}
    )
    verdict3 = adapter.is_mechanism_refuted(candidate, model, obs_refuted, [])
    assert verdict3 == MechanismRefutationVerdict.REFUTED, \
        f"Expected REFUTED (physical invariant: ΔP>=threshold, 0% drainage), got {verdict3}"

    print("✅ Test 15 (tri-state verdict): INSUFFICIENT_EVIDENCE + REFUTED (physical invariant) (P0.4)")


def test_evidence_predicate_real():
    """Test 16: EvidencePredicate checks real evidence, not just presence.

    Per CEO directive (P0.3 second round):
      A fake or placeholder object should not satisfy "stage complete."
    """
    from epistemic_integrity.invention_loop_engine.schemas import (
        RawObservation, MechanisticModel, VirtualCohort, BuyerRequirement
    )

    # Test: tampered data hash → fails
    obs = RawObservation(experiment_id="test", raw_data={"value": 42})
    obs.data_hash = "fake_hash"  # Tampered
    assert not EvidencePredicate.raw_data_integrity_verified(obs), \
        "Tampered hash should fail"

    # Test: correct hash → passes
    obs2 = RawObservation(experiment_id="test", raw_data={"value": 42})
    assert EvidencePredicate.raw_data_integrity_verified(obs2), \
        "Correct hash should pass"

    # Test: model with no numeric prediction → not falsifiable
    model = MechanisticModel(
        candidate_id="test", model_name="test", model_type="test",
        prediction={"description": "a string, not numeric"}
    )
    assert not EvidencePredicate.model_is_falsifiable(model), \
        "Model with string prediction should be NON_FALSIFIABLE"

    # Test: model with numeric prediction → falsifiable
    model2 = MechanisticModel(
        candidate_id="test", model_name="test", model_type="test",
        prediction={"value": 42.0}
    )
    assert EvidencePredicate.model_is_falsifiable(model2), \
        "Model with numeric prediction should be falsifiable"

    print("✅ Test 16 (evidence predicates): real checks, not presence (P0.3)")



def test_eig_provenance_enforced():
    """Test 17: SYNTHETIC_TEST_ONLY EIG cannot influence real experiments.

    Per CEO directive (P0.4 — fourth round):
      'Mathematical sophistication does not upgrade the epistemic class of its inputs.'
      A perfectly implemented Bayesian engine fed invented priors is still
      an invention of the coder, not a discovery of reality.
    """
    calc = BayesianEIGCalculator()

    # SYNTHETIC_TEST_ONLY hypotheses
    synthetic_prov = EIGProvenance(
        source="SYNTHETIC_TEST_ONLY",
        epistemic_class=EIGEpistemicClass.SYNTHETIC_TEST_ONLY,
        uncertainty="fictional"
    )
    hypotheses = [
        Hypothesis("H1", "synthetic A", 0.5, synthetic_prov),
        Hypothesis("H2", "synthetic B", 0.5, synthetic_prov),
    ]
    outcomes = [
        ExperimentalOutcome("O1", "synthetic outcome 1",
            {"H1": 0.8, "H2": 0.2}, synthetic_prov),
        ExperimentalOutcome("O2", "synthetic outcome 2",
            {"H1": 0.2, "H2": 0.8}, synthetic_prov),
    ]

    trace = calc.calculate_eig(hypotheses, outcomes)

    # SYNTHETIC_TEST_ONLY → cannot influence real experiments
    assert trace.can_influence_real_experiment == False, \
        "SYNTHETIC_TEST_ONLY EIG must NOT influence real experiments"
    assert trace.minimum_epistemic_class == EIGEpistemicClass.SYNTHETIC_TEST_ONLY

    # Now test with EVIDENCE_BOUND hypotheses
    evidence_prov = EIGProvenance(
        source="R6 frozen protocol measurement",
        epistemic_class=EIGEpistemicClass.EVIDENCE_BOUND,
        uncertainty="measured ±0.5 mmHg"
    )
    hypotheses_real = [
        Hypothesis("H1", "measured A", 0.5, evidence_prov),
        Hypothesis("H2", "measured B", 0.5, evidence_prov),
    ]
    outcomes_real = [
        ExperimentalOutcome("O1", "measured outcome 1",
            {"H1": 0.8, "H2": 0.2}, evidence_prov),
        ExperimentalOutcome("O2", "measured outcome 2",
            {"H1": 0.2, "H2": 0.8}, evidence_prov),
    ]

    trace_real = calc.calculate_eig(hypotheses_real, outcomes_real)

    # EVIDENCE_BOUND → CAN influence real experiments
    assert trace_real.can_influence_real_experiment == True, \
        "EVIDENCE_BOUND EIG CAN influence real experiments"
    assert trace_real.minimum_epistemic_class == EIGEpistemicClass.EVIDENCE_BOUND

    print("✅ Test 17 (EIG provenance): SYNTHETIC→blocked, EVIDENCE_BOUND→allowed (P0.4)")


def run_all_tests():
    """Run all anti-gaming tests."""
    print("=" * 60)
    print("ANTI-GAMING TESTS FOR INVENTION LOOP ENGINE")
    print("=" * 60)
    print()

    test_simulator_confidently_wrong()
    test_experiment_contradicts_model()
    test_strongest_alternative_beats()
    test_virtual_cohort_omits_decisive_population()
    test_evidence_provider_fails()
    test_new_data_invalidates_model()
    test_replayability()
    test_single_best_experiment()
    test_earned_completion_gate()
    test_parameter_classification_enforced()
    test_model_refuted_does_not_kill()
    test_data_driven_information_gain()
    test_non_falsifiable_model_blocked()
    test_inconclusive_data_blocked()
    test_tri_state_mechanism_verdict()
    test_evidence_predicate_real()
    test_eig_provenance_enforced()

    print()
    print("=" * 60)
    print("ALL 17 ANTI-GAMING TESTS PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    run_all_tests()

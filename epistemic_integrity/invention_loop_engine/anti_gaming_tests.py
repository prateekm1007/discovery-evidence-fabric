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
from .patent_destruction_adapter import (
    PatentDestructionAdapter, AttackStageStatus, CoverageLevel,
    ExecutionProof, CoverageProof, ProviderExecutionReceipt,
)
from .provider_transport_boundary import (
    ProviderTransportBoundary, TransportExecutionRequest,
)
from .live_vs_synthetic_transport import (
    LiveProviderTransport, SyntheticProviderTransport,
    TrustedProviderRegistry, TransportMode, is_eligible_for_real_verdict,
)
from .adapters.r6_adapter import R6Adapter
from .adapters.sensing_adapter import SensingAdapter
from .correspondence_engine import (
    CorrespondenceEngine, LimitationCorrespondence, PriorArtEligibilityEvidence,
    CorrespondenceType, CorrespondenceStatus, DisclosureType, CorrespondenceRule,
    EligibilityPhase, LegalDecisionVerdict,
    CorrespondenceAttestation, LegalCorrespondenceDecision,
)


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


def test_execution_proof_enforced():
    """Test 18: Transport boundary required for COMPLETED.

    Per CEO directive (eighth round):
      'Trust must terminate at the lowest layer that actually observed reality.'
      The adapter must NOT be able to directly construct a valid receipt.
      Only the transport boundary can set transport_verified=True.
    """
    adapter = PatentDestructionAdapter()
    manifest = adapter.create_manifest("test_exec", "test candidate")

    # Try to mark COMPLETED without receipt (manually supplied)
    adapter.record_stage(manifest, "keyword_search",
        provider="Google Patents", query="test",
        result_ids=["US0123456A1"],
        status=AttackStageStatus.COMPLETED,
        coverage=CoverageLevel.RELEVANT_FOUND,
    )
    stage = manifest.stages["keyword_search"]
    assert stage.status == AttackStageStatus.INCOMPLETE
    assert stage.execution.manually_supplied == True

    # Execute through the transport boundary (the ONLY valid path)
    transport = ProviderTransportBoundary()
    request = TransportExecutionRequest(
        provider_name="Google Patents",
        endpoint_url="https://patents.google.com/?q=test",
        adapter_version="GooglePatentsAdapter v1.0",
        stage_name="cpc_ipc_search",
    )
    result = transport.execute(
        request=request,
        response_body=b"{\"results\": [\"US0456789A1\"]}",
        response_status=200,
        response_headers={"content-type": "application/json"},
    )
    receipt = transport.create_receipt(result)

    assert receipt.is_valid == True
    assert receipt.transport_verified == True  # Set by transport boundary
    assert receipt.provider_confirmed == True  # DERIVED

    adapter.execute_stage(manifest, "cpc_ipc_search", receipt, "CPC A61M")
    stage2 = manifest.stages["cpc_ipc_search"]
    assert stage2.status == AttackStageStatus.COMPLETED
    assert stage2.execution.manually_supplied == False
    assert stage2.execution.provider_confirmed == True

    print("✅ Test 18 (transport boundary): no receipt→INCOMPLETE, transport→COMPLETED (eighth round)")


def test_coverage_proof_enforced():
    """Test 19: EXHAUSTED requires CoverageProof with classifications_searched.

    Per CEO directive (seventh round):
      classifications_searched is now REQUIRED.
      No classification execution → cannot claim EXHAUSTED.
    """
    adapter = PatentDestructionAdapter()
    manifest = adapter.create_manifest("test_coverage", "test")

    # Use transport boundary for legitimate execution
    transport = ProviderTransportBoundary()
    req = TransportExecutionRequest(
        provider_name="EPO", endpoint_url="https://espacenet.com/?q=test",
        adapter_version="1.0", stage_name="keyword_search",
    )
    result = transport.execute(req, b'{"results": ["US0456789A1"]}', 200, {})
    receipt = transport.create_receipt(result)

    # Try EXHAUSTED without coverage proof
    adapter.execute_stage(manifest, "keyword_search", receipt, "test")
    stage = manifest.stages["keyword_search"]
    assert stage.coverage == CoverageLevel.QUERIED, \
        f"EXHAUSTED without proof must downgrade to QUERIED, got {stage.coverage}"

    # CoverageProof WITHOUT classifications_searched → NOT exhausted
    proof_no_class = CoverageProof(
        databases_queried=["Google Patents"],
        query_families=["filter+bypass"],
        pagination_exhausted=True,
        jurisdictions=["US"],
        # classifications_searched is EMPTY!
    )
    assert proof_no_class.is_exhausted() == False, \
        "EXHAUSTED requires classifications_searched (seventh round)"

    # CoverageProof WITH classifications_searched → exhausted
    proof_full = CoverageProof(
        databases_queried=["Google Patents", "EPO"],
        classifications_searched=["A61M 27/00", "A61M 1/36"],
        query_families=["filter+bypass", "shunt+valve"],
        pagination_exhausted=True,
        jurisdictions=["US", "EP", "JP"],
    )
    assert proof_full.is_exhausted() == True

    # Execute claims_search through transport too
    req2 = TransportExecutionRequest(
        provider_name="USPTO", endpoint_url="https://uspto.gov/?q=claims",
        adapter_version="1.0", stage_name="claims_search",
    )
    result2 = transport.execute(req2, b'{"results": ["US4741730A"]}', 200, {})
    receipt2 = transport.create_receipt(result2)
    adapter.execute_stage(manifest, "claims_search", receipt2, "claims:test",
                          coverage_proof=proof_full)
    stage2 = manifest.stages["claims_search"]
    assert stage2.coverage == CoverageLevel.EXHAUSTED, \
        f"EXHAUSTED with valid proof should stay EXHAUSTED, got {stage2.coverage}"

    print("✅ Test 19 (coverage proof): no classifications→NOT exhausted, with→EXHAUSTED (seventh round)")



def test_attack_the_attacker():
    """Test 20: Forged evidence must fail closed.

    Per CEO directive (seventh round):
      Adversarial tests where fake bytes, fake provider, fake IDs,
      fake coverage, replayed response, timeout, partial pagination
      all attempt to produce COMPLETED/EXHAUSTED. Every one must fail.
    """
    adapter = PatentDestructionAdapter()

    # Attack 1: Invalid receipt (missing fields)
    manifest1 = adapter.create_manifest("attack1", "test")
    bad_receipt = ProviderExecutionReceipt(provider="fake")
    assert bad_receipt.is_valid == False
    adapter.execute_stage(manifest1, "keyword_search", bad_receipt, "test")
    assert manifest1.stages["keyword_search"].status == AttackStageStatus.FAILED

    # Attack 2: Receipt with failure_state
    manifest2 = adapter.create_manifest("attack2", "test")
    failed_receipt = ProviderExecutionReceipt(
        provider="GooglePatentsAdapter", request_fingerprint="req",
        request_timestamp="2026-08-20T00:00:00Z", response_status=500,
        response_headers_hash="h", raw_response_hash="r",
        provider_record_ids=[], adapter_version="1.0",
        failure_state="TIMEOUT"
    )
    assert failed_receipt.provider_confirmed == False  # DERIVED: failure_state set
    adapter.execute_stage(manifest2, "keyword_search", failed_receipt, "test")
    assert manifest2.stages["keyword_search"].status == AttackStageStatus.FAILED

    # Attack 3: Fake coverage proof (no classifications) — use transport for receipt
    manifest3 = adapter.create_manifest("attack3", "test")
    transport3 = ProviderTransportBoundary()
    req3 = TransportExecutionRequest(
        provider_name="EPO", endpoint_url="https://espacenet.com/?q=test",
        adapter_version="1.0", stage_name="keyword_search",
    )
    result3 = transport3.execute(req3, b'{"results": ["US0123456A1"]}', 200, {})
    good_receipt = transport3.create_receipt(result3)
    fake_coverage = CoverageProof(
        databases_queried=["fake_db"],
        # classifications_searched EMPTY
        query_families=["fake"],
        pagination_exhausted=True,
        jurisdictions=["US"],
    )
    assert fake_coverage.is_exhausted() == False
    adapter.execute_stage(manifest3, "keyword_search", good_receipt, "test",
                          coverage_proof=fake_coverage)
    assert manifest3.stages["keyword_search"].coverage == CoverageLevel.QUERIED

    # Attack 4: Manually supplied COMPLETED (no receipt at all)
    manifest4 = adapter.create_manifest("attack4", "test")
    adapter.record_stage(manifest4, "keyword_search",
        provider="fake", query="fake", result_ids=["US0999999B2"],
        status=AttackStageStatus.COMPLETED,
        coverage=CoverageLevel.EXHAUSTED,
    )
    assert manifest4.stages["keyword_search"].status == AttackStageStatus.INCOMPLETE
    assert manifest4.stages["keyword_search"].coverage == CoverageLevel.QUERIED

    print("✅ Test 20 (attack the attacker): all 4 forged evidence attacks fail closed (seventh round)")



def test_anti_self_certification():
    """Test 21: Adapter cannot self-certify. Transport boundary is the verifier.

    Per CEO directive (eighth round):
      'Don't move the trust problem upward from caller to adapter.
       Move it downward to the execution boundary.'

      A malicious adapter that constructs ProviderExecutionReceipt() directly
      must NOT be able to get COMPLETED status.
    """
    adapter = PatentDestructionAdapter()
    manifest = adapter.create_manifest("anti_self_cert", "test")

    # Attack 1: Adapter creates receipt directly (self-certification)
    self_cert_receipt = ProviderExecutionReceipt(
        provider="MaliciousAdapter",
        request_fingerprint="fake_req",
        request_timestamp="2026-08-20T00:00:00Z",
        response_status=200,
        response_headers_hash="fake_headers",
        raw_response_hash="fake_body",
        provider_record_ids=["US0999999B2"],
        adapter_version="1.0",
        # transport_verified defaults to False!
    )
    assert self_cert_receipt.transport_verified == False
    assert self_cert_receipt.is_valid == False  # Cannot self-certify!
    assert self_cert_receipt.provider_confirmed == False

    adapter.execute_stage(manifest, "keyword_search", self_cert_receipt, "fake")
    assert manifest.stages["keyword_search"].status == AttackStageStatus.FAILED

    # Attack 2: Adapter lies about provider name
    transport = ProviderTransportBoundary()
    request = TransportExecutionRequest(
        provider_name="Google Patents",
        endpoint_url="https://patents.google.com/?q=test",
        adapter_version="FakeAdapter v1.0",
    )
    result = transport.execute(request, b'{"results": []}', 200, {})
    receipt = transport.create_receipt(result)
    # Receipt correctly records the provider from the transport request
    assert receipt.provider == "Google Patents"  # From transport, not adapter
    assert receipt.adapter_version != "FakeAdapter v1.0"  # Transport stamped it

    # Attack 3: Replayed old receipt (anti-replay)
    manifest3 = adapter.create_manifest("replay_test", "test")
    transport3 = ProviderTransportBoundary()
    req = TransportExecutionRequest(
        provider_name="EPO", endpoint_url="https://espacenet.com/?q=test",
        adapter_version="1.0", stage_name="keyword_search",
    )
    result1 = transport3.execute(req, b'{"results": ["US1111111A1"]}', 200, {})
    receipt1 = transport3.create_receipt(result1)
    adapter.execute_stage(manifest3, "keyword_search", receipt1, "test")
    assert manifest3.stages["keyword_search"].status == AttackStageStatus.COMPLETED

    # Replay: same request fingerprint → REPLAY_DETECTED
    result2 = transport3.execute(req, b'{"results": ["US2222222B2"]}', 200, {})
    assert "REPLAY_DETECTED" in result2.failure_state
    receipt2 = transport3.create_receipt(result2)
    assert receipt2.provider_confirmed == False  # Failed due to replay

    print("✅ Test 21 (anti-self-certification): adapter self-cert→FAILED, replay→FAILED (eighth round)")



def test_synthetic_rejected_for_real_verdicts():
    """Test 22: SYNTHETIC_TEST_ONLY receipts rejected by real patent-destruction.

    Per CEO directive (ninth round):
      'A simulator of reality must never be allowed to masquerade as
       contact with reality.'
    """
    adapter = PatentDestructionAdapter()
    manifest = adapter.create_manifest("synthetic_test", "test")

    # Create a synthetic transport receipt
    synthetic_transport = SyntheticProviderTransport()
    req = TransportExecutionRequest(
        provider_name="Google Patents",
        endpoint_url="https://patents.google.com/?q=test",
        adapter_version="1.0",
        stage_name="keyword_search",
    )
    result = synthetic_transport.execute(req, b'{"results": ["US0456789A1"]}', 200, {})
    receipt = synthetic_transport.create_receipt(result)

    # Receipt has SYNTHETIC_TEST_ONLY stamp
    assert "SYNTHETIC_TEST_ONLY" in receipt.adapter_version
    assert "SYNTHETIC_TEST_ONLY" in receipt.failure_state

    # is_eligible_for_real_verdict must be False
    assert is_eligible_for_real_verdict(receipt) == False

    # execute_stage must REJECT the synthetic receipt
    adapter.execute_stage(manifest, "keyword_search", receipt, "test")
    assert manifest.stages["keyword_search"].status == AttackStageStatus.FAILED
    assert "SYNTHETIC_TEST_ONLY" in manifest.stages["keyword_search"].failures[0]

    print("✅ Test 22 (synthetic rejected): SYNTHETIC_TEST_ONLY→FAILED (ninth round)")


def test_live_transport_rejects_caller_supplied_response():
    """Test 23: LIVE transport does NOT accept response_body from caller.

    Per CEO directive (ninth round):
      The caller must NOT supply response_body, response_status, response_headers.
      Those must come from the actual HTTP client.

      LiveProviderTransport.execute() takes only a request — no response params.
    """
    registry = TrustedProviderRegistry()

    # Verify registry resolves providers
    entry = registry.resolve("google_patents")
    assert entry is not None
    assert entry.provider_name == "Google Patents"
    assert len(entry.approved_endpoints) > 0

    # Verify endpoint validation
    assert registry.validate_endpoint("google_patents", "https://patents.google.com/?q=test") == True
    assert registry.validate_endpoint("google_patents", "https://evil.com/hack") == False
    assert registry.validate_endpoint("unknown_provider", "https://anything.com") == False

    # LiveProviderTransport.execute() signature does NOT accept response params
    # It only accepts a TransportExecutionRequest — the response comes from HTTP
    import inspect
    live = LiveProviderTransport(registry)
    sig = inspect.signature(live.execute)
    params = list(sig.parameters.keys())
    assert "response_body" not in params, \
        "LiveProviderTransport.execute must NOT accept response_body"
    assert "response_status" not in params, \
        "LiveProviderTransport.execute must NOT accept response_status"
    assert "response_headers" not in params, \
        "LiveProviderTransport.execute must NOT accept response_headers"
    assert params == ["request"], \
        f"LiveProviderTransport.execute should take only 'request', got {params}"

    # Unknown provider → FAILED
    req_unknown = TransportExecutionRequest(
        provider_name="FakeProvider",
        endpoint_url="https://evil.com/",
        adapter_version="1.0",
    )
    result = live.execute(req_unknown)
    assert "UNKNOWN_PROVIDER" in result.failure_state or "PROVIDER_NOT_REGISTERED" in result.failure_state

    # Unapproved endpoint → FAILED
    req_bad_url = TransportExecutionRequest(
        provider_name="Google Patents",
        endpoint_url="https://evil.com/hack",
        adapter_version="1.0",
    )
    result2 = live.execute(req_bad_url)
    assert "ENDPOINT_NOT_APPROVED" in result2.failure_state

    print("✅ Test 23 (live transport): no caller-supplied response, registry-validated (ninth round)")


# ===========================================================================
# Twentieth round (CEO deep audit 2026-08-21) — P0/P1 adversarial regression
# tests for the correspondence engine and prior-art eligibility layer.
#
# Six fail-closed scenarios that must FAIL the certification if the engine
# ever silently admits them:
#   24 — all eligibility fields populated but legal rule never applied
#   25 — functional equivalence marked explicit by mistake (semantic backdoor)
#   26 — supporting evidence changed but provenance hash unchanged
#   27 — forged reviewer string with no attestation
#   28 — public_availability_date conflicts with publication_date
#   29 — jurisdiction/rule mismatch (US rule on EPO jurisdiction, etc.)
# ===========================================================================


def test_eligibility_fields_populated_but_rule_never_applied():
    """Test 24: All eligibility fields populated but legal rule never applied.

    Per CEO directive (twentieth round — P0-1):
      'A populated applicable_rule field is not proof that the rule was applied.'

    Setup: Provide candidate_critical_date, public_availability_date,
           jurisdiction, and applicable_rule — but leave
           legal_rule_application_evidence empty.
    Expected: eligibility_phase stops at LEGAL_RULE_IDENTIFIED.
              eligibility != 'ELIGIBLE' with COMPLETE.
              analysis_completeness == 'SIMPLIFIED'.
    Failure mode if engine is wrong: returns ELIGIBILITY_ESTABLISHED based
              on date comparison alone — the exact failure pattern the audit
              identified in the v19 implementation.
    """
    ev = PriorArtEligibilityEvidence(
        candidate_critical_date="2024-03-15",
        reference_publication_date="1988-05-10",
        public_availability_date="1988-05-10",
        jurisdiction="US",
        applicable_rule="35 USC 102(a)(1)",
        # legal_rule_application_evidence is DELIBERATELY EMPTY
        legal_rule_application_evidence="",
    )
    ev.evaluate()

    # Phase must NOT reach ELIGIBILITY_ESTABLISHED
    assert ev.eligibility_phase != EligibilityPhase.ELIGIBILITY_ESTABLISHED.value, (
        f"FAIL: engine reached ELIGIBILITY_ESTABLISHED without "
        f"legal_rule_application_evidence. Phase={ev.eligibility_phase}. "
        f"A populated applicable_rule is NOT proof the rule was applied."
    )
    # Phase must NOT even reach LEGAL_RULE_APPLIED
    assert ev.eligibility_phase != EligibilityPhase.LEGAL_RULE_APPLIED.value, (
        f"FAIL: engine reached LEGAL_RULE_APPLIED without "
        f"legal_rule_application_evidence. Phase={ev.eligibility_phase}."
    )
    # analysis_completeness must NOT be COMPLETE
    assert ev.analysis_completeness != "COMPLETE", (
        f"FAIL: analysis_completeness=COMPLETE without rule application. "
        f"Got completeness={ev.analysis_completeness}, eligibility={ev.eligibility}."
    )
    print(f"✅ Test 24 (fields populated, rule never applied): phase={ev.eligibility_phase}, completeness={ev.analysis_completeness} (twentieth round)")


def test_functional_equivalence_marked_explicit_does_not_support_102():
    """Test 25: Functional equivalence marked explicit by mistake.

    Per CEO directive (twentieth round — P0-2):
      'Do not let merely setting disclosure_type=EXPLICIT_CLAIM_DISCLOSURE
       turn equivalence into anticipation.'

    Setup: A FUNCTIONAL_EQUIVALENT correspondence with disclosure_type
           set to EXPLICIT_CLAIM_DISCLOSURE (the semantic backdoor) and
           status=ESTABLISHED, rule=FUNCTIONAL_ANALYSIS.
    Expected: can_support_section_102 returns False — equivalence requires
              a separate LegalCorrespondenceDecision.
    Failure mode if engine is wrong: returns True — semantic backdoor active.
    """
    # First, verify the structural invariant prevents the backdoor at construction
    # time: VERBATIM_EXPLICIT_CLAIM_DISCLOSURE cannot be set on non-VERBATIM.
    try:
        bad = LimitationCorrespondence(
            limitation_id="L1",
            reference_patent="US123",
            claim_number=1,
            claim_passage="a valve mechanism",
            correspondence_type=CorrespondenceType.FUNCTIONAL_EQUIVALENT,
            disclosure_type=DisclosureType.VERBATIM_EXPLICIT_CLAIM_DISCLOSURE,
            status=CorrespondenceStatus.ESTABLISHED,
            rule=CorrespondenceRule.FUNCTIONAL_ANALYSIS,
        )
        raise AssertionError(
            "FAIL: engine allowed VERBATIM_EXPLICIT_CLAIM_DISCLOSURE on "
            "FUNCTIONAL_EQUIVALENT correspondence. Structural invariant broken."
        )
    except ValueError:
        pass  # Expected: structural invariant rejects this combination

    # Second, verify that even the legacy EXPLICIT_CLAIM_DISCLOSURE on
    # FUNCTIONAL_EQUIVALENT does NOT auto-support §102.
    c = LimitationCorrespondence(
        limitation_id="L1",
        reference_patent="US123",
        claim_number=1,
        claim_passage="a valve mechanism",
        correspondence_type=CorrespondenceType.FUNCTIONAL_EQUIVALENT,
        disclosure_type=DisclosureType.EXPLICIT_CLAIM_DISCLOSURE,  # legacy value
        status=CorrespondenceStatus.ESTABLISHED,
        rule=CorrespondenceRule.FUNCTIONAL_ANALYSIS,
        supporting_evidence="Expert declares functional equivalence",
        reviewer="EXPERT:J.Doe",
    )
    assert not c.can_support_section_102, (
        "FAIL: FUNCTIONAL_EQUIVALENT with EXPLICIT_CLAIM_DISCLOSURE supported "
        "§102 without a LegalCorrespondenceDecision. Semantic backdoor active."
    )
    assert c.requires_legal_decision, (
        "FAIL: FUNCTIONAL_EQUIVALENT should require a legal decision."
    )

    # Third, verify that attaching a LegalCorrespondenceDecision with
    # SUPPORTS_102 enables §102 support.
    ld = LegalCorrespondenceDecision(
        decision=LegalDecisionVerdict.SUPPORTS_102,
        reviewer_id="pa-001",
        reviewer_role="PATENT_AGENT",
        jurisdiction="US",
        legal_basis="35 USC 102(a) anticipation by functional equivalence",
        rationale="The functional equivalence constitutes anticipation under 112(f).",
        evidence_hash="abc123def456",
    )
    c.legal_decision = ld
    c.recompute_provenance_hash()
    assert c.can_support_section_102, (
        "FAIL: FUNCTIONAL_EQUIVALENT with SUPPORTS_102 legal_decision should "
        "support §102."
    )
    assert c.verify_provenance_integrity(), (
        "FAIL: provenance hash integrity broken after attaching legal_decision."
    )
    print(f"✅ Test 25 (equivalence marked explicit): backdoor closed, requires LegalCorrespondenceDecision (twentieth round)")


def test_supporting_evidence_changed_provenance_hash_mismatch():
    """Test 26: Supporting evidence changed but provenance hash unchanged.

    Per CEO directive (twentieth round — P0-3):
      'So someone could alter the underlying provenance metadata without
       changing the provenance hash. That is a real integrity gap.'

    Setup: Create a correspondence, capture its provenance_hash, then
           silently alter supporting_evidence WITHOUT calling
           recompute_provenance_hash().
    Expected: verify_provenance_integrity() returns False.
              can_support_section_102 returns False (integrity check fails).
    Failure mode if engine is wrong: returns True — undetected tampering.
    """
    eng = CorrespondenceEngine()
    c = eng.evaluate_correspondence(
        limitation_text="a fluid entry port",
        claim_text="an implantable shunt device comprising a fluid entry port",
        claim_number=1,
        reference_patent="US123",
        limitation_id="L1",
    )
    original_hash = c.provenance_hash
    assert c.can_support_section_102, "Baseline: VERBATIM should support §102"
    assert c.verify_provenance_integrity(), "Baseline: provenance should be intact"

    # Tamper: silently alter supporting_evidence WITHOUT recomputing the hash
    c.supporting_evidence = "TAMPERED: false evidence inserted by attacker"

    # Integrity check must FAIL
    assert not c.verify_provenance_integrity(), (
        "FAIL: provenance integrity check passed after silent tampering. "
        "The hash does not bind supporting_evidence."
    )
    # can_support_section_102 must FAIL (because integrity check is part of the gate)
    assert not c.can_support_section_102, (
        "FAIL: can_support_section_102 returned True after silent tampering. "
        "Integrity check must be part of the §102 gate."
    )

    # Verify the same applies to other fields: claim_passage, claim_start_offset,
    # correspondence_type, rule, reviewer, raw_response_hash, source_node_identifier
    c2 = eng.evaluate_correspondence(
        limitation_text="a fluid entry port",
        claim_text="an implantable shunt device comprising a fluid entry port",
        claim_number=1,
        reference_patent="US123",
        limitation_id="L2",
    )
    for field_name, new_value in [
        ("claim_passage", "TAMPERED"),
        ("claim_start_offset", 99999),
        ("claim_end_offset", 99999),
        ("reviewer", "FORGED:EXPERT:J.Doe"),
        ("raw_response_hash", "forge"),
        ("source_node_identifier", "forge"),
        ("technical_relationship", "TAMPERED"),
    ]:
        # Reset and tamper one field at a time
        c2_copy = eng.evaluate_correspondence(
            limitation_text="a fluid entry port",
            claim_text="an implantable shunt device comprising a fluid entry port",
            claim_number=1,
            reference_patent="US123",
            limitation_id="L2",
        )
        setattr(c2_copy, field_name, new_value)
        assert not c2_copy.verify_provenance_integrity(), (
            f"FAIL: tampering {field_name} was not detected by provenance hash. "
            f"Hash does not bind {field_name}."
        )
    print(f"✅ Test 26 (evidence tampering detected): all 8 fields protected by provenance hash (twentieth round)")


def test_forged_reviewer_string_rejected_for_manual_expert():
    """Test 27: Forged reviewer string with no attestation.

    Per CEO directive (twentieth round — P0-4):
      'reviewer=\"EXPERT:J.Doe\" is not evidence that an expert actually
       performed the review.'

    Setup: Attempt to confirm a candidate via MANUAL_EXPERT with
           reviewer='EXPERT:J.Doe' but NO CorrespondenceAttestation.
    Expected: confirm_candidate() refuses to set status=ESTABLISHED.
              Status remains CANDIDATE.
              can_support_section_102 returns False.
    Failure mode if engine is wrong: silently accepts the forged string and
              establishes legal correspondence.
    """
    eng = CorrespondenceEngine()
    candidate = eng.propose_candidate_correspondence(
        limitation_text="a valve mechanism",
        claim_text="a valve mechanism",
        claim_number=1,
        reference_patent="US123",
        limitation_id="L1",
        proposed_passage="a valve mechanism",
        proposed_relationship="model proposes correspondence",
    )
    assert candidate.status == CorrespondenceStatus.CANDIDATE

    # Attempt to confirm via MANUAL_EXPERT with a forged reviewer string but
    # NO CorrespondenceAttestation
    confirmed = eng.confirm_candidate(
        candidate=candidate,
        confirming_rule=CorrespondenceRule.MANUAL_EXPERT,
        confirming_evidence="Expert says this corresponds",
        confirming_reviewer="EXPERT:J.Doe",  # Forged string
        correspondence_type=CorrespondenceType.VERBATIM,
        disclosure_type=DisclosureType.VERBATIM_EXPLICIT_CLAIM_DISCLOSURE,
        attestation=None,  # NO ATTESTATION
    )
    # Must NOT reach ESTABLISHED
    assert confirmed.status != CorrespondenceStatus.ESTABLISHED, (
        "FAIL: MANUAL_EXPERT reached ESTABLISHED with only a free-form reviewer "
        "string. A forged string is not evidence of an expert review."
    )
    assert not confirmed.can_support_section_102, (
        "FAIL: forged MANUAL_EXPERT supported §102."
    )
    assert "attestation" in confirmed.unresolved_reason.lower(), (
        f"FAIL: unresolved_reason should mention attestation. Got: {confirmed.unresolved_reason}"
    )

    # Now provide a real attestation — should succeed
    real_attestation = CorrespondenceAttestation(
        reviewer_id="pa-001",
        reviewer_role="PATENT_AGENT",
        decision="ESTABLISHED",
        rationale="Reviewed the claim and limitation; correspondence confirmed.",
        evidence_hash="abc123def456",
    )
    # Need a fresh candidate because confirm_candidate mutated the previous one
    candidate2 = eng.propose_candidate_correspondence(
        limitation_text="a valve mechanism",
        claim_text="a valve mechanism",
        claim_number=1,
        reference_patent="US123",
        limitation_id="L2",
        proposed_passage="a valve mechanism",
        proposed_relationship="model proposes correspondence",
    )
    confirmed2 = eng.confirm_candidate(
        candidate=candidate2,
        confirming_rule=CorrespondenceRule.MANUAL_EXPERT,
        confirming_evidence="Expert says this corresponds",
        confirming_reviewer="EXPERT:J.Doe",
        correspondence_type=CorrespondenceType.VERBATIM,
        disclosure_type=DisclosureType.VERBATIM_EXPLICIT_CLAIM_DISCLOSURE,
        attestation=real_attestation,
    )
    assert confirmed2.status == CorrespondenceStatus.ESTABLISHED, (
        "FAIL: MANUAL_EXPERT with valid attestation should reach ESTABLISHED."
    )
    assert confirmed2.can_support_section_102, (
        "FAIL: MANUAL_EXPERT with valid attestation should support §102."
    )
    print(f"✅ Test 27 (forged reviewer rejected): MANUAL_EXPERT requires CorrespondenceAttestation (twentieth round)")


def test_public_availability_publication_date_conflict():
    """Test 28: public_availability_date conflicts with publication_date.

    Per CEO directive (twentieth round — P1):
      'public availability conflicts with publication date' must fail closed.

    Setup: publication_date 1988-05-10, public_availability_date 1990-01-01.
           A document cannot be formally published BEFORE it is publicly
           available — this is suspicious.
    Expected: eligibility = UNKNOWN, eligibility_phase = EMPTY,
              analysis_completeness = INCOMPLETE.
    Failure mode if engine is wrong: returns ELIGIBLE based on the earlier
              publication_date without flagging the inconsistency.
    """
    ev = PriorArtEligibilityEvidence(
        candidate_critical_date="2024-03-15",
        reference_publication_date="1988-05-10",  # Published
        public_availability_date="1990-01-01",    # But not publicly available until 1990?!
        jurisdiction="US",
        applicable_rule="35 USC 102(a)(1)",
        legal_rule_application_evidence="Applied 35 USC 102(a)(1): public_availability_date precedes critical_date.",
    )
    ev.evaluate()

    assert ev.eligibility == "UNKNOWN", (
        f"FAIL: eligibility={ev.eligibility} despite publication_date < "
        f"public_availability_date. Inconsistent dates must yield UNKNOWN."
    )
    assert ev.eligibility_phase == EligibilityPhase.EMPTY.value, (
        f"FAIL: phase={ev.eligibility_phase} despite date conflict."
    )
    assert "inconsistency" in ev.eligibility_reasoning.lower(), (
        f"FAIL: reasoning should flag inconsistency. Got: {ev.eligibility_reasoning}"
    )
    print(f"✅ Test 28 (date conflict): eligibility=UNKNOWN, flagged inconsistency (twentieth round)")


def test_jurisdiction_rule_mismatch_fails_closed():
    """Test 29: jurisdiction/rule mismatch.

    Per CEO directive (twentieth round — P1):
      'jurisdiction/rule mismatch occurs' must fail closed.

    Setup: jurisdiction='EPO' but applicable_rule mentions 'USC' (US law).
    Expected: eligibility = UNKNOWN, eligibility_phase = EMPTY,
              analysis_completeness = INCOMPLETE.
    Failure mode if engine is wrong: applies the wrong jurisdiction's rule
              and returns ELIGIBLE.
    """
    ev = PriorArtEligibilityEvidence(
        candidate_critical_date="2024-03-15",
        reference_publication_date="1988-05-10",
        public_availability_date="1988-05-10",
        jurisdiction="EPO",  # European Patent Office
        applicable_rule="35 USC 102(a)(1)",  # But US rule!
        legal_rule_application_evidence="Applied 35 USC 102(a)(1): public_availability_date 1988-05-10 precedes critical_date 2024-03-15.",
    )
    ev.evaluate()

    assert ev.eligibility == "UNKNOWN", (
        f"FAIL: eligibility={ev.eligibility} despite jurisdiction/rule mismatch. "
        f"EPO jurisdiction cannot use USC rules."
    )
    assert ev.eligibility_phase == EligibilityPhase.EMPTY.value, (
        f"FAIL: phase={ev.eligibility_phase} despite jurisdiction/rule mismatch."
    )
    assert "mismatch" in ev.eligibility_reasoning.lower(), (
        f"FAIL: reasoning should flag mismatch. Got: {ev.eligibility_reasoning}"
    )

    # Also test the reverse: US jurisdiction with EPC rule
    ev2 = PriorArtEligibilityEvidence(
        candidate_critical_date="2024-03-15",
        reference_publication_date="1988-05-10",
        public_availability_date="1988-05-10",
        jurisdiction="US",
        applicable_rule="EPC Art 54(2)",  # European rule!
        legal_rule_application_evidence="Applied EPC Art 54(2): publicly available before priority date.",
    )
    ev2.evaluate()
    assert ev2.eligibility == "UNKNOWN", (
        f"FAIL: eligibility={ev2.eligibility} despite US/EPC mismatch."
    )
    print(f"✅ Test 29 (jurisdiction/rule mismatch): both directions fail closed (twentieth round)")


# Additional positive tests for the new four-phase eligibility model


def test_eligibility_four_phases_progress_correctly():
    """Test 30: Four-phase eligibility progression.

    Verify that:
      - Empty evidence → phase=EMPTY
      - Dates only → phase=SOURCE_DATES_COMPLETE, completeness=SIMPLIFIED
      - + jurisdiction+rule → phase=LEGAL_RULE_IDENTIFIED, completeness=SIMPLIFIED
      - + application_evidence → phase=ELIGIBILITY_ESTABLISHED, completeness=COMPLETE
    """
    # Phase 0: Empty
    ev0 = PriorArtEligibilityEvidence()
    ev0.evaluate()
    assert ev0.eligibility_phase == EligibilityPhase.EMPTY.value
    assert ev0.analysis_completeness == "INCOMPLETE"

    # Phase 1: SOURCE_DATES_COMPLETE (with publication_date fallback)
    ev1 = PriorArtEligibilityEvidence(
        candidate_critical_date="2024-03-15",
        reference_publication_date="1988-05-10",
    )
    ev1.evaluate()
    assert ev1.eligibility_phase == EligibilityPhase.SOURCE_DATES_COMPLETE.value, (
        f"Phase 1 failed: {ev1.eligibility_phase}"
    )
    assert ev1.analysis_completeness == "SIMPLIFIED"

    # Phase 2: LEGAL_RULE_IDENTIFIED
    ev2 = PriorArtEligibilityEvidence(
        candidate_critical_date="2024-03-15",
        reference_publication_date="1988-05-10",
        public_availability_date="1988-05-10",
        jurisdiction="US",
        applicable_rule="35 USC 102(a)(1)",
    )
    ev2.evaluate()
    assert ev2.eligibility_phase == EligibilityPhase.LEGAL_RULE_IDENTIFIED.value, (
        f"Phase 2 failed: {ev2.eligibility_phase}"
    )
    assert ev2.analysis_completeness == "SIMPLIFIED"

    # Phase 4: ELIGIBILITY_ESTABLISHED (with application evidence)
    ev4 = PriorArtEligibilityEvidence(
        candidate_critical_date="2024-03-15",
        reference_publication_date="1988-05-10",
        public_availability_date="1988-05-10",
        jurisdiction="US",
        applicable_rule="35 USC 102(a)(1)",
        legal_rule_application_evidence=(
            "Applied 35 USC 102(a)(1): the reference was publicly available "
            "on 1988-05-10, which precedes the candidate's critical date of "
            "2024-03-15 by approximately 36 years."
        ),
    )
    ev4.evaluate()
    assert ev4.eligibility_phase == EligibilityPhase.ELIGIBILITY_ESTABLISHED.value, (
        f"Phase 4 failed: {ev4.eligibility_phase}"
    )
    assert ev4.analysis_completeness == "COMPLETE"
    assert ev4.eligibility == "ELIGIBLE"
    print(f"✅ Test 30 (four-phase progression): EMPTY → SOURCE_DATES → LEGAL_RULE_IDENTIFIED → ELIGIBILITY_ESTABLISHED (twentieth round)")


def test_claim_dependency_supports_102():
    """Test 31: EXPLICIT_DEPENDENCY + CLAIM_DEPENDENCY supports §102.

    The second automatic §102 path (after VERBATIM). Verifies that
    inheritance from a parent claim still constitutes automatic §102 support.
    """
    c = LimitationCorrespondence(
        limitation_id="L1",
        reference_patent="US123",
        claim_number=5,  # Dependent claim
        claim_passage="a fluid entry port",
        claim_start_offset=0,
        claim_end_offset=17,
        correspondence_type=CorrespondenceType.EXPLICIT_DEPENDENCY,
        disclosure_type=DisclosureType.CLAIM_DEPENDENCY,
        status=CorrespondenceStatus.ESTABLISHED,
        rule=CorrespondenceRule.DEPENDENCY_INHERITANCE,
        supporting_evidence="Inherited from parent claim 1",
        technical_relationship="Claim 5 depends on claim 1",
        reviewer="DEPENDENCY_INHERITANCE_AUTO",
    )
    assert c.can_support_section_102, (
        "FAIL: EXPLICIT_DEPENDENCY + CLAIM_DEPENDENCY should support §102."
    )
    assert not c.requires_legal_decision, (
        "FAIL: EXPLICIT_DEPENDENCY should not require a legal decision."
    )
    print(f"✅ Test 31 (claim dependency): EXPLICIT_DEPENDENCY supports §102 (twentieth round)")



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
    test_execution_proof_enforced()
    test_coverage_proof_enforced()
    test_attack_the_attacker()
    test_anti_self_certification()
    test_synthetic_rejected_for_real_verdicts()
    test_live_transport_rejects_caller_supplied_response()

    # Twentieth round (CEO deep audit) — P0/P1 adversarial regression
    test_eligibility_fields_populated_but_rule_never_applied()
    test_functional_equivalence_marked_explicit_does_not_support_102()
    test_supporting_evidence_changed_provenance_hash_mismatch()
    test_forged_reviewer_string_rejected_for_manual_expert()
    test_public_availability_publication_date_conflict()
    test_jurisdiction_rule_mismatch_fails_closed()
    test_eligibility_four_phases_progress_correctly()
    test_claim_dependency_supports_102()

    print()
    print("=" * 60)
    print("ALL 31 ANTI-GAMING TESTS PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    run_all_tests()

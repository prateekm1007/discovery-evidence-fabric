"""
Abstract base class for invention loop adapters.

Each adapter provides domain-specific implementations of:
- prove_problem: Article XX problem-existence gate
- build_causal_graph: edge-by-edge causal chain with epistemic marking
- attack_strongest_alternative: why wouldn't existing solutions dominate?
- build_simulator: mechanistic model that tries to KILL the candidate
- run_vvuq: verification, validation, UQ, applicability domain
- generate_virtual_cohort: adversarial patient/device scenarios
- design_experiments: falsification experiment design
- evaluate_model_prediction: did the model survive the experiment?
- identify_remaining_uncertainties: what do we still not know?
- propose_next_falsification: the SINGLE next experiment
- generate_regulatory_evidence: FDA CM&S, ASME V&V 40
"""

from __future__ import annotations

import abc
from typing import Any, Optional
import random

from ..schemas import (
    Candidate, CausalGraph, Experiment, FalsificationProposal,
    MechanisticModel, ModelUpdate, ProblemHypothesis, RawObservation,
    RegulatoryEvidence, UncertaintyBudget, VirtualCohort,
)


class InventionLoopAdapter(abc.ABC):
    """Abstract base class for domain-specific invention loop adapters.

    One engine, four adapters. The engine provides the common loop;
    the adapter provides the domain-specific epistemic machinery.
    """

    @property
    @abc.abstractmethod
    def adapter_name(self) -> str:
        """Human-readable name for this adapter."""
        pass

    @property
    @abc.abstractmethod
    def target_slot(self) -> int:
        """Which portfolio slot (1-4) this adapter serves."""
        pass

    @abc.abstractmethod
    def prove_problem(self, candidate: Candidate) -> ProblemHypothesis:
        """Article XX problem-existence gate.

        Must answer all 5 questions:
        1. Does the failure mode actually occur?
        2. Does it matter to the buyer?
        3. Does the mechanism change the relevant physical quantity?
        4. Is the change large enough to matter?
        5. Does the intervention create a larger failure mode?

        Returns GREEN / YELLOW / RED for each question.
        """
        pass

    @abc.abstractmethod
    def build_causal_graph(self, candidate: Candidate) -> CausalGraph:
        """Build the edge-by-edge causal chain.

        Each edge must have:
        - evidence_type: DIRECT_MEASUREMENT / ANIMAL / TRANSPORT_MODEL / ANALOGY
        - epistemic_class: HYPOTHESIS / MODEL_DERIVED / DEMONSTRATED / REFUTED / BLOCKED

        Do NOT let strong evidence at one edge carry an unknown edge.
        Do NOT let generic analogy upgrade a specific edge.
        """
        pass

    @abc.abstractmethod
    def attack_strongest_alternative(self, candidate: Candidate,
                                      causal_graph: CausalGraph) -> dict:
        """Attack the candidate with the strongest existing alternative.

        Must determine: does the alternative DOMINATE (proven superiority)
        or merely EXIST (unproven superiority)?

        Returns:
            {
                "alternative_name": str,
                "dominates": bool,  # True only if PROVEN superiority
                "reasoning": str,
            }
        """
        pass

    @abc.abstractmethod
    def build_simulator(self, candidate: Candidate,
                         causal_graph: CausalGraph) -> MechanisticModel:
        """Build a mechanistic simulator that tries to KILL the candidate.

        The simulator is ADVERSARIAL — it actively searches for failure modes.
        It does not validate; it tries to falsify.
        """
        pass

    @abc.abstractmethod
    def run_vvuq(self, model: MechanisticModel) -> UncertaintyBudget:
        """Verification, Validation, Uncertainty Quantification, Applicability.

        Per CEO directive: do NOT implement confidence scores.
        VVUQ must be explicit:
        - Verification: is the code correct?
        - Validation: does the model match experiment?
        - UQ: what are the uncertainty bounds?
        - Applicability: where is the model valid?
        """
        pass

    @abc.abstractmethod
    def generate_virtual_cohort(self, candidate: Candidate,
                                 model: MechanisticModel,
                                 budget: UncertaintyBudget,
                                 rng: random.Random) -> VirtualCohort:
        """Generate adversarial virtual patient/device cohort.

        Per CEO directive: the loop must actively search for
        signal-confounding states, not merely optimize performance.
        Adversarial cases must be included.
        """
        pass

    @abc.abstractmethod
    def design_experiments(self, candidate: Candidate,
                            model: MechanisticModel,
                            cohort: VirtualCohort,
                            budget: UncertaintyBudget) -> list[Experiment]:
        """Design falsification experiments.

        Returns multiple candidate experiments. The engine will rank them
        and select the SINGLE best by information gain.
        """
        pass

    @abc.abstractmethod
    def evaluate_model_prediction(self, model: MechanisticModel,
                                   observation: RawObservation) -> bool:
        """Evaluate whether the model prediction survived the experiment.

        Returns True if the model survived (prediction matched observation).
        Returns False if the model was REFUTED (prediction contradicted).

        Per CEO directive: model predictions MUST remain distinguishable
        from experimental observations.
        """
        pass

    @abc.abstractmethod
    def is_mechanism_refuted(self, candidate: Candidate,
                              model: MechanisticModel,
                              observation: RawObservation,
                              updates: list[ModelUpdate]) -> bool:
        """Determine if a model refutation means the MECHANISM is impossible.

        Per CEO directive (P0.1 — critical):
          A model can be WRONG while the invention remains viable.
          MODEL_REFUTED → MODEL_REVISION / NEW_EXPERIMENT
          unless an explicit causal rule establishes that the MECHANISM
          itself is impossible.

        This method implements the adapter-specific causal rule:
          - If the model failure is due to a modeling assumption → return False
            (revise model, try again)
          - If the model failure is due to a physical impossibility of the
            mechanism → return True (kill candidate)

        Per Article XXIX: separate implementation failure from mechanism failure.
          prototype failure → embodiment failure → mechanism failure → invention failure
          Each promotion requires separate evidence.
        """
        pass

    @abc.abstractmethod
    def calculate_information_gain(self, candidate: Candidate,
                                    budget: UncertaintyBudget,
                                    experiment: "Experiment",
                                    observations: list[RawObservation]) -> float:
        """Calculate the expected information gain of an experiment.

        Per CEO directive (P0.4): this must be a DATA-DRIVEN calculation from:
          uncertainty → candidate outcomes → expected posterior uncertainty → cost/risk

        NOT a manually supplied score.

        Returns: expected information gain (float, higher = more informative)
        """
        pass

    @abc.abstractmethod
    def identify_remaining_uncertainties(self, candidate: Candidate,
                                          budget: UncertaintyBudget,
                                          observations: list[RawObservation],
                                          updates: list[ModelUpdate]) -> list[str]:
        """Identify what we still don't know after experiments.

        The loop uses this to decide what the next experiment should test.
        """
        pass

    @abc.abstractmethod
    def propose_next_falsification(self, candidate: Candidate,
                                    budget: UncertaintyBudget,
                                    observations: list[RawObservation],
                                    updates: list[ModelUpdate],
                                    rng: random.Random) -> FalsificationProposal:
        """Propose the SINGLE next falsification experiment.

        Per CEO directive: 'this is the single experiment that would reduce
        our uncertainty the most or most efficiently kill the invention.'
        NOT 'here are ten experiments.'
        """
        pass

    @abc.abstractmethod
    def generate_regulatory_evidence(self, candidate: Candidate,
                                      budget: UncertaintyBudget,
                                      observations: list[RawObservation],
                                      updates: list[ModelUpdate]) -> RegulatoryEvidence:
        """Generate regulatory evidence (FDA CM&S, ASME V&V 40).

        Must include:
        - FDA risk-informed credibility assessment
        - ASME V&V 40 compliance
        - In-silico cohort evidence
        - Physical experiment evidence
        """
        pass

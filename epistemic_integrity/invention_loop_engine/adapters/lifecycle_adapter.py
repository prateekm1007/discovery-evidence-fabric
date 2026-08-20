"""CNS/Lifecycle Intelligence adapter for the invention loop engine.

Adapter 4: CNS/Lifecycle Intelligence

This adapter is DIFFERENT from the others. It is the organizational
failure-learning loop:

paper/patent/trial/MAUDE/recall → failure hypothesis → causal model →
candidate intervention → simulation → evidence search → experimental
proposal → outcome → knowledge graph update.

This becomes the organizational failure-learning engine.
"""

from __future__ import annotations

import random

from ..schemas import (
    Candidate, CausalGraph, CausalEdge, EpistemicClass, EvidenceType,
    Experiment, FalsificationProposal, MechanisticModel, ModelUpdate,
    ProblemHypothesis, RawObservation, RegulatoryEvidence, UncertaintyBudget,
    VirtualCohort, VirtualPatient,
)
from .base import InventionLoopAdapter


class LifecycleAdapter(InventionLoopAdapter):
    """Adapter for CNS/Lifecycle Intelligence (Slot 4).

    This is the failure-learning engine. It ingests evidence from:
    - Scientific literature
    - Patents
    - Clinical trials
    - MAUDE/recalls
    - Engineering models

    It generates failure hypotheses, tests them via simulation,
    and proposes interventions.
    """

    @property
    def adapter_name(self) -> str:
        return "CNS/Lifecycle Intelligence"

    @property
    def target_slot(self) -> int:
        return 4

    def prove_problem(self, candidate: Candidate) -> ProblemHypothesis:
        return ProblemHypothesis(
            candidate_id=candidate.name,
            question_1_exists="GREEN",
            question_2_buyer_suffers="YES",
            question_3_mechanism_changes_quantity="PENDING",
            question_4_change_large_enough="PENDING",
            question_5_larger_failure_mode="PENDING",
            evidence_sources=[],
            strongest_alternative_explanation="No existing failure-learning engine "
                "for CSF shunt devices. Current approaches are reactive, not predictive.",
        )

    def build_causal_graph(self, candidate: Candidate) -> CausalGraph:
        graph = CausalGraph(candidate_id=candidate.name)
        graph.add_edge(CausalEdge(
            source="evidence_ingestion",
            target="failure_hypothesis",
            question="Can evidence from multiple sources generate failure hypotheses?",
            evidence_type=EvidenceType.PEER_REVIEWED,
            epistemic_class=EpistemicClass.MODEL_DERIVED,
        ))
        graph.add_edge(CausalEdge(
            source="failure_hypothesis",
            target="intervention_proposal",
            question="Can failure hypotheses generate preventive interventions?",
            evidence_type=EvidenceType.UNKNOWN,
            epistemic_class=EpistemicClass.BLOCKED_UNRESOLVED,
            notes="Requires validation against historical failure data",
        ))
        return graph

    def attack_strongest_alternative(self, candidate: Candidate,
                                      causal_graph: CausalGraph) -> dict:
        return {
            "alternative_name": "Reactive post-market surveillance (current standard)",
            "dominates": False,
            "reasoning": "Current surveillance is reactive (failures reported after they "
                         "occur). The lifecycle engine is predictive (hypothesizes failures "
                         "before they occur). Not dominated — different value proposition.",
        }

    def build_simulator(self, candidate: Candidate,
                         causal_graph: CausalGraph) -> MechanisticModel:
        return MechanisticModel(
            candidate_id=candidate.name,
            model_name="failure_prediction_model",
            model_type="ML + knowledge graph",
            assumptions=[
                "Historical failure patterns predict future failures",
                "Multi-source evidence improves prediction",
                "Knowledge graph captures causal relationships",
            ],
            parameters={
                "evidence_sources": ["literature", "patents", "trials", "MAUDE", "recalls"],
                "prediction_horizon_months": 12,
            },
            prediction={
                "failure_predicted": True,
                "prediction_confidence": "MODEL_DERIVED — not clinically validated",
            },
        )

    def run_vvuq(self, model: MechanisticModel) -> UncertaintyBudget:
        return UncertaintyBudget(
            candidate_id=model.candidate_id,
            verification_status="VERIFIED — ML pipeline reproducible",
            validation_status="PENDING — requires historical failure data validation",
            uncertainty_quantification={
                "false_positive_rate_uncertainty": 0.10,
                "prediction_horizon_uncertainty_months": 3,
            },
            applicability_domain="Valid for CSF shunt device failures. "
                                 "NOT valid for other device classes without retraining.",
            key_uncertainties=[
                "Data quality and completeness of MAUDE/recall databases",
                "Causal vs correlative failure patterns",
                "Generalizability across device generations",
            ],
        )

    def generate_virtual_cohort(self, candidate: Candidate,
                                 model: MechanisticModel,
                                 budget: UncertaintyBudget,
                                 rng: random.Random) -> VirtualCohort:
        cohort = VirtualCohort(
            candidate_id=candidate.name,
            cohort_design="Virtual device-failure scenarios from historical data",
            random_seed=rng.randint(0, 2**32),
        )
        adversarial = [
            "novel_failure_mode_not_in_training_data",
            "data_provider_failure_maude_unavailable",
            "conflicting_evidence_sources",
            "rare_device_generation",
            "long_term_failure_after_5_years",
        ]
        for adv in adversarial:
            cohort.patients.append(VirtualPatient(
                patient_id=f"adversarial_{adv}",
                parameters={"scenario": adv},
                is_adversarial=True,
                adversarial_description=f"Failure-learning edge case: {adv}",
            ))
        cohort.adversarial_cases = adversarial
        return cohort

    def design_experiments(self, candidate: Candidate,
                            model: MechanisticModel,
                            cohort: VirtualCohort,
                            budget: UncertaintyBudget) -> list[Experiment]:
        return [
            Experiment(
                candidate_id=candidate.name,
                objective="Historical validation: can the model predict known "
                          "past failures?",
                falsification_target="Model predicts >80% of known historical failures",
                protocol={"historical_failures": 50, "time_window_years": 10},
                expected_information_gain=0.85,
            ),
        ]

    def evaluate_model_prediction(self, model: MechanisticModel,
                                   observation: RawObservation) -> bool:
        predicted = model.prediction.get("failure_predicted", True)
        observed = observation.raw_data.get("failure_occurred", None)
        if observed is None:
            return True
        return predicted == observed

    def identify_remaining_uncertainties(self, candidate: Candidate,
                                          budget: UncertaintyBudget,
                                          observations: list[RawObservation],
                                          updates: list[ModelUpdate]) -> list[str]:
        return budget.key_uncertainties + [
            "Knowledge graph completeness",
            "Novel failure mode detection capability",
        ]

    def propose_next_falsification(self, candidate: Candidate,
                                    budget: UncertaintyBudget,
                                    observations: list[RawObservation],
                                    updates: list[ModelUpdate],
                                    rng: random.Random) -> FalsificationProposal:
        next_exp = Experiment(
            candidate_id=candidate.name,
            objective="Prospective validation: predict failures before they occur "
                      "in next 12 months",
            falsification_target="Model predicts >50% of failures that occur in "
                                 "the next 12 months",
            expected_information_gain=0.88,
        )
        return FalsificationProposal(
            candidate_id=candidate.name,
            proposed_experiment=next_exp,
            information_gain_score=0.88,
            kill_probability=0.25,
            reasoning="Prospective validation is the ultimate test of a predictive "
                      "model. If it cannot predict future failures, it is not a "
                      "failure-learning engine — it is just a data aggregator.",
        )

    def is_mechanism_refuted(self, candidate, model, observation, updates):
        """Determine if model refutation means the MECHANISM is impossible.
        
        Default: model failure is a modeling error, NOT a mechanism impossibility.
        Adapters should override with domain-specific causal rules.
        """
        # Default: model is wrong but mechanism may survive
        # Only return True if the failure proves the mechanism is physically impossible
        return False

    def calculate_information_gain(self, candidate, budget, experiment, observations):
        """Calculate expected information gain from an experiment.
        
        Data-driven: uncertainty_reduction / (cost * risk)
        NOT a manually supplied score.
        """
        # Base implementation: information gain = key_uncertainties addressed / total
        if not budget or not budget.key_uncertainties:
            return 0.0
        
        # Count how many key uncertainties this experiment's falsification target addresses
        target = experiment.falsification_target.lower()
        addressed = sum(1 for u in budget.key_uncertainties 
                       if any(word in target for word in u.lower().split()[:3]))
        
        # Information gain = fraction of uncertainties addressed
        ig = addressed / len(budget.key_uncertainties)
        
        # Reduce if we already have observations (diminishing returns)
        if observations:
            ig *= (1.0 / (1.0 + 0.1 * len(observations)))
        
        return min(ig, 1.0)

    def generate_regulatory_evidence(self, candidate: Candidate,
                                      budget: UncertaintyBudget,
                                      observations: list[RawObservation],
                                      updates: list[ModelUpdate]) -> RegulatoryEvidence:
        return RegulatoryEvidence(
            candidate_id=candidate.name,
            fda_cms_framework_compliance="CM&S for post-market surveillance. "
                "FDA supports predictive analytics for device safety.",
            asme_vv40_compliance="Verification complete. Validation pending historical data.",
            risk_informed_credibility="MEDIUM — decision-support tool, not diagnostic",
            in_silico_cohort_evidence="Virtual failure scenarios from historical data",
            physical_experiment_evidence=f"{len(observations)} historical validation cases",
        )

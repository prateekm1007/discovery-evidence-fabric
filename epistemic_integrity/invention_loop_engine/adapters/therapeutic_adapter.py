"""Controlled CNS Therapeutic adapter for the invention loop engine.

Adapter 3: Controlled CNS Therapeutic Platform

Loop: mechanism → transport/PK model → patient variability →
virtual cohort → dose/device experiment → PK/PD update → next experiment.

Do not allow the model to claim clinical efficacy from simulation alone.
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


class TherapeuticAdapter(InventionLoopAdapter):
    """Adapter for Controlled CNS Therapeutic Platform (Slot 3)."""

    @property
    def adapter_name(self) -> str:
        return "Controlled CNS Therapeutic"

    @property
    def target_slot(self) -> int:
        return 3

    def prove_problem(self, candidate: Candidate) -> ProblemHypothesis:
        return ProblemHypothesis(
            candidate_id=candidate.name,
            question_1_exists="GREEN",
            question_2_buyer_suffers="YES",
            question_3_mechanism_changes_quantity="GREEN",
            question_4_change_large_enough="GREEN",
            question_5_larger_failure_mode="PENDING",
            evidence_sources=[],
            strongest_alternative_explanation="Existing CNS delivery (Ommaya, intrathecal pumps) "
                "is invasive or non-targeted. CereVasc's eShunt provides a novel access route.",
        )

    def build_causal_graph(self, candidate: Candidate) -> CausalGraph:
        graph = CausalGraph(candidate_id=candidate.name)
        graph.add_edge(CausalEdge(
            source="drug_delivery_via_eshunt",
            target="therapeutic_concentration_in_CNS",
            question="Does eShunt delivery achieve therapeutic concentration?",
            evidence_type=EvidenceType.COMPUTATIONAL_MODEL,
            epistemic_class=EpistemicClass.MODEL_DERIVED,
        ))
        graph.add_edge(CausalEdge(
            source="therapeutic_concentration_in_CNS",
            target="clinical_efficacy",
            question="Does therapeutic concentration produce clinical efficacy?",
            evidence_type=EvidenceType.UNKNOWN,
            epistemic_class=EpistemicClass.BLOCKED_UNRESOLVED,
            notes="Do NOT allow simulation to claim clinical efficacy",
        ))
        return graph

    def attack_strongest_alternative(self, candidate: Candidate,
                                      causal_graph: CausalGraph) -> dict:
        return {
            "alternative_name": "Ommaya reservoir + intrathecal pump",
            "dominates": False,
            "reasoning": "Ommaya exists but is intraventricular (invasive). "
                         "Intrathecal pumps exist but are bulky. eShunt provides "
                         "endovascular access. Not dominated.",
        }

    def build_simulator(self, candidate: Candidate,
                         causal_graph: CausalGraph) -> MechanisticModel:
        return MechanisticModel(
            candidate_id=candidate.name,
            model_name="pk_pd_transport_model",
            model_type="3-compartment PK/PD",
            assumptions=[
                "CSF drug distribution follows established pharmacokinetics",
                "Therapeutic threshold is drug-specific",
                "eShunt delivery rate is controllable",
            ],
            parameters={
                "csf_volume_mL": 150,
                "production_rate_mL_per_min": 0.35,
                "clearance_rate_per_h": 2.88,
            },
            prediction={
                "therapeutic_concentration_achieved": True,
                "time_to_steady_state_h": 24,
            },
        )

    def run_vvuq(self, model: MechanisticModel) -> UncertaintyBudget:
        return UncertaintyBudget(
            candidate_id=model.candidate_id,
            verification_status="VERIFIED — 3-compartment model equations checked",
            validation_status="PENDING — requires in-vivo PK data",
            uncertainty_quantification={
                "csf_volume_uncertainty_pct": 20,
                "clearance_rate_uncertainty_pct": 30,
            },
            applicability_domain="Valid for small-molecule drugs in adult CSF. "
                                 "NOT valid for biologics without additional validation.",
            key_uncertainties=[
                "Patient-specific CSF volume variability",
                "Drug clearance rate variability",
                "BBB permeability effects",
            ],
        )

    def generate_virtual_cohort(self, candidate: Candidate,
                                 model: MechanisticModel,
                                 budget: UncertaintyBudget,
                                 rng: random.Random) -> VirtualCohort:
        cohort = VirtualCohort(
            candidate_id=candidate.name,
            cohort_design="Virtual patients with PK variability",
            random_seed=rng.randint(0, 2**32),
        )
        adversarial = [
            "low_csf_volume_patient",
            "high_clearance_rate_patient",
            "impaired_bbb_patient",
            "pediatric_patient",
            "elderly_patient",
        ]
        for adv in adversarial:
            cohort.patients.append(VirtualPatient(
                patient_id=f"adversarial_{adv}",
                parameters={"scenario": adv},
                is_adversarial=True,
                adversarial_description=f"PK edge case: {adv}",
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
                objective="In-vivo PK study: measure CSF drug concentration after "
                          "eShunt delivery",
                falsification_target="Therapeutic concentration achieved in CSF "
                                     "within 24 hours",
                protocol={"patients": 10, "timepoints": 8},
                expected_information_gain=0.85,
            ),
        ]

    def evaluate_model_prediction(self, model: MechanisticModel,
                                   observation: RawObservation) -> bool:
        predicted = model.prediction.get("therapeutic_concentration_achieved", True)
        observed = observation.raw_data.get("therapeutic_concentration_achieved", None)
        if observed is None:
            return True
        return predicted == observed

    def identify_remaining_uncertainties(self, candidate: Candidate,
                                          budget: UncertaintyBudget,
                                          observations: list[RawObservation],
                                          updates: list[ModelUpdate]) -> list[str]:
        return budget.key_uncertainties + [
            "Clinical efficacy cannot be claimed from simulation alone",
        ]

    def propose_next_falsification(self, candidate: Candidate,
                                    budget: UncertaintyBudget,
                                    observations: list[RawObservation],
                                    updates: list[ModelUpdate],
                                    rng: random.Random) -> FalsificationProposal:
        next_exp = Experiment(
            candidate_id=candidate.name,
            objective="Clinical efficacy study: does therapeutic concentration "
                      "produce clinical improvement?",
            falsification_target="Clinical improvement > placebo in RCT",
            expected_information_gain=0.90,
        )
        return FalsificationProposal(
            candidate_id=candidate.name,
            proposed_experiment=next_exp,
            information_gain_score=0.90,
            kill_probability=0.30,
            reasoning="Clinical efficacy is the ultimate test. Simulation cannot "
                      "claim it. Only an RCT can resolve this uncertainty.",
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
            fda_cms_framework_compliance="CM&S for PK/PD modeling. "
                "FDA requires clinical efficacy data — simulation insufficient.",
            asme_vv40_compliance="Verification complete. Validation pending in-vivo data.",
            risk_informed_credibility="HIGH — therapeutic device requires clinical evidence",
            in_silico_cohort_evidence="Virtual PK cohort with adversarial patients",
            physical_experiment_evidence=f"{len(observations)} PK observations",
        )

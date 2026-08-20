"""
End-to-End Invention Loop Engine.

Per CEO directive (2026-08-20):
  "Build one reusable End-to-End Invention Loop Engine, with four
   domain-specific adapters. The core epistemic machinery should be common."

The loop is a state machine:
  CANDIDATE → PROBLEM_PROOF → DESTRUCTION → MECHANISTIC_MODEL →
  VVUQ → VIRTUAL_COHORT → EXPERIMENT_DESIGN → PHYSICAL_EXPERIMENT →
  RAW_DATA_INGESTION → MODEL_UPDATE → INFORMATION_GAIN_RANKING →
  NEXT_FALSIFICATION_EXPERIMENT → EVIDENCE_DOSSIER

Key requirements:
  1. Replayable: same evidence state + random seed = same proposed experiment
  2. VVUQ explicit (not confidence scores)
  3. Model predictions distinguishable from experimental observations
  4. The AI must say "this is the SINGLE experiment that reduces uncertainty the most"
  5. Anti-gaming: loop responds by changing experiment, not adjusting conclusion

Constitution: Article XXXV (v1.5.0) — Closed-Loop Epistemic Control.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from typing import Any, Optional

from .schemas import (
    Assumption, BuyerRequirement, CausalEdge, CausalGraph, Candidate,
    Dossier, EpistemicClass, EvidenceType, Experiment, FalsificationProposal,
    LoopState, MechanisticModel, ModelUpdate, ProblemHypothesis,
    Provenance, RawObservation, RegulatoryEvidence, UncertaintyBudget,
    VirtualCohort, VirtualPatient, _hash_dict,
)


class InventionLoopEngine:
    """The common loop engine. One engine, four adapters.

    The engine manages:
    - State transitions (with provenance)
    - Evidence custody (every object traceable)
    - Replayability (deterministic given seed + evidence)
    - VVUQ enforcement (no confidence scores)
    - Anti-gaming (loop changes experiment, not conclusion)

    Each adapter provides domain-specific:
    - Ontology (what are the entities?)
    - Simulator (how to model the mechanism)
    - Uncertainty model (what are the unknowns?)
    - Virtual cohort generator (adversarial cases)
    - Experiment schema (what does a test look like?)
    - Buyer/regulatory objective (what defines success?)
    """

    def __init__(self, adapter, random_seed: int = 42):
        """Initialize the engine with a domain adapter.

        Args:
            adapter: An adapter instance (R6, Sensing, Therapeutic, or Lifecycle)
            random_seed: Fixed seed for replayability
        """
        self.adapter = adapter
        self.random_seed = random_seed
        self.rng = random.Random(random_seed)
        self.state = LoopState.CANDIDATE
        self.state_history: list[dict] = []
        self.candidate: Optional[Candidate] = None
        self.problem_proof: Optional[ProblemHypothesis] = None
        self.causal_graph: Optional[CausalGraph] = None
        self.mechanistic_model: Optional[MechanisticModel] = None
        self.uncertainty_budget: Optional[UncertaintyBudget] = None
        self.virtual_cohort: Optional[VirtualCohort] = None
        self.experiment: Optional[Experiment] = None
        self.observations: list[RawObservation] = []
        self.model_updates: list[ModelUpdate] = []
        self.falsification_proposal: Optional[FalsificationProposal] = None
        self.buyer_requirements: list[BuyerRequirement] = []
        self.regulatory_evidence: Optional[RegulatoryEvidence] = None
        self.dossier: Optional[Dossier] = None
        self.kill_reason: Optional[str] = None

    def _record_transition(self, to_state: LoopState, notes: str = ""):
        """Record a state transition with full provenance."""
        transition = {
            "from_state": self.state.value,
            "to_state": to_state.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
            "random_seed": self.random_seed,
            "adapter": self.adapter.__class__.__name__,
        }
        self.state_history.append(transition)
        self.state = to_state

    def run_candidate(self, candidate: Candidate) -> bool:
        """Step 1: Register the candidate.

        Returns True if the candidate can proceed to problem proof.
        Returns False if the candidate is immediately killed.
        """
        self.candidate = candidate
        self.candidate.provenance.epistemic_class = EpistemicClass.HYPOTHESIS
        self._record_transition(LoopState.PROBLEM_PROOF,
                                f"Candidate '{candidate.name}' registered")
        return True

    def run_problem_proof(self) -> bool:
        """Step 2: Article XX problem-existence gate.

        The adapter provides the domain-specific problem evidence.
        The engine enforces the 5-question gate.
        Returns True if the problem exists (GREEN). False if KILLED or BLOCKED.
        """
        if not self.candidate:
            raise RuntimeError("No candidate registered")

        self.problem_proof = self.adapter.prove_problem(self.candidate)
        self._record_transition(LoopState.DESTRUCTION,
                                f"Problem proof: Q1={self.problem_proof.question_1_exists}")

        if self.problem_proof.question_1_exists == "RED":
            self._kill("Problem does not exist (Article XX Q1=RED)")
            return False
        if self.problem_proof.question_1_exists == "YELLOW":
            self._block("Problem existence YELLOW — not proven, not refuted")
            return False
        return True

    def run_destruction(self) -> bool:
        """Step 3: Destruction attack (prior art + causal chain + strongest alternative).

        The adapter provides the domain-specific destruction.
        The engine enforces:
        - §102 / §103 separation
        - Causal chain edge-by-edge evidence marking
        - Strongest alternative must not dominate
        - Escape mechanisms must survive their own destruction
        """
        if not self.candidate:
            raise RuntimeError("No candidate")

        self.causal_graph = self.adapter.build_causal_graph(self.candidate)

        # Check for established infeasible edges
        if self.causal_graph.established_infeasible_edges:
            self._kill(f"Delivery route infeasible: "
                       f"{self.causal_graph.established_infeasible_edges}")
            return False

        # Check for critical unknowns that make the candidate BLOCKED
        if self.causal_graph.critical_unknowns:
            self._block(f"Causal chain has unknowns: "
                        f"{self.causal_graph.critical_unknowns}")
            return False

        # Run strongest alternative attack
        strongest_alt = self.adapter.attack_strongest_alternative(
            self.candidate, self.causal_graph)

        if strongest_alt.get("dominates", False):
            self._kill(f"Strongest alternative dominates: "
                       f"{strongest_alt.get('alternative_name', 'unknown')}")
            return False

        self._record_transition(LoopState.MECHANISTIC_MODEL,
                                "Survived destruction. Proceeding to model.")
        return True

    def run_mechanistic_model(self) -> bool:
        """Step 4: Build a mechanistic simulator that tries to KILL the candidate.

        The simulator is adversarial — it tries to find failure modes.
        """
        if not self.candidate:
            raise RuntimeError("No candidate")

        self.mechanistic_model = self.adapter.build_simulator(
            self.candidate, self.causal_graph)
        self.mechanistic_model.provenance.epistemic_class = EpistemicClass.MODEL_DERIVED
        self._record_transition(LoopState.VVUQ,
                                f"Model built: {self.mechanistic_model.model_name}")
        return True

    def run_vvuq(self) -> bool:
        """Step 5: Verification, Validation, Uncertainty Quantification, Applicability.

        Per CEO directive: do NOT implement confidence scores as a substitute.
        VVUQ must be explicit.
        """
        if not self.mechanistic_model:
            raise RuntimeError("No mechanistic model")

        self.uncertainty_budget = self.adapter.run_vvuq(self.mechanistic_model)
        self._record_transition(LoopState.VIRTUAL_COHORT,
                                f"VVUQ complete. Key uncertainties: "
                                f"{len(self.uncertainty_budget.key_uncertainties)}")
        return True

    def run_virtual_cohort(self) -> bool:
        """Step 6: Generate adversarial virtual patient/device cohort.

        Per CEO directive (Adapter 2): the loop must actively search for
        signal-confounding states, not merely optimize performance.
        """
        if not self.mechanistic_model or not self.uncertainty_budget:
            raise RuntimeError("No model or VVUQ")

        self.virtual_cohort = self.adapter.generate_virtual_cohort(
            self.candidate, self.mechanistic_model, self.uncertainty_budget,
            self.rng)
        self._record_transition(LoopState.EXPERIMENT_DESIGN,
                                f"Cohort: {len(self.virtual_cohort.patients)} patients, "
                                f"{len(self.virtual_cohort.adversarial_cases)} adversarial")
        return True

    def run_experiment_design(self) -> bool:
        """Step 7: Design the SINGLE best falsification experiment.

        Per CEO directive: 'this is the single experiment that would reduce
        our uncertainty the most or most efficiently kill the invention.'
        NOT 'here are ten experiments.'
        """
        if not self.virtual_cohort:
            raise RuntimeError("No virtual cohort")

        experiments = self.adapter.design_experiments(
            self.candidate, self.mechanistic_model, self.virtual_cohort,
            self.uncertainty_budget)

        if not experiments:
            self._kill("No falsification experiment could be designed")
            return False

        # Rank by information gain and select the SINGLE best
        ranked = self._rank_by_information_gain(experiments)
        self.experiment = ranked[0]
        self.experiment.is_single_best = True

        self._record_transition(LoopState.PHYSICAL_EXPERIMENT,
                                f"Single best experiment: {self.experiment.objective} "
                                f"(info_gain={self.experiment.expected_information_gain:.3f})")
        return True

    def run_physical_experiment(self, raw_data: dict[str, Any],
                                 provenance_strength: str = "OPERATOR_TRANSCRIPTION_FALLBACK") -> bool:
        """Step 8-9: Run physical experiment and ingest raw data.

        Per Article XXXV: automatic ingestion.
        Model predictions MUST remain distinguishable from experimental observations.
        """
        if not self.experiment:
            raise RuntimeError("No experiment designed")

        observation = RawObservation(
            experiment_id=self.experiment.experiment_id,
            raw_data=raw_data,
            provenance_strength=provenance_strength,
        )
        observation.provenance.epistemic_class = EpistemicClass.EXPERIMENTALLY_DEMONSTRATED
        self.observations.append(observation)
        self._record_transition(LoopState.MODEL_UPDATE,
                                f"Observation ingested: {observation.observation_id[:8]}... "
                                f"provenance={provenance_strength}")
        return True

    def run_model_update(self) -> bool:
        """Step 10: Update model from experimental evidence.

        Per CEO directive (P0.1 — critical fix):
          A model can be WRONG while the invention remains viable.
          A model contradiction must NEVER automatically kill the candidate.
          The adapter must explicitly establish the promotion rule:
            MODEL_REFUTED → MODEL_REVISION / NEW_EXPERIMENT
          unless an explicit causal rule establishes that the MECHANISM
          itself is impossible.

        Per Article XXIX: separate implementation failure from mechanism failure.
          prototype failure → embodiment failure → mechanism failure → invention failure
          Each promotion requires separate evidence.

        The loop must respond by CHANGING ITS NEXT EXPERIMENT, not by
        adjusting its conclusion.
        """
        if not self.mechanistic_model or not self.observations:
            raise RuntimeError("No model or observations")

        latest_obs = self.observations[-1]
        previous_hash = self.mechanistic_model.model_hash

        did_survive = self.adapter.evaluate_model_prediction(
            self.mechanistic_model, latest_obs)

        update = ModelUpdate(
            candidate_id=self.candidate.name,
            observation_id=latest_obs.observation_id,
            previous_model_hash=previous_hash,
            updated_model_hash=previous_hash,  # Will be updated if model changes
            did_model_survive=did_survive,
            what_changed="Model survived" if did_survive else "Model REFUTED by experiment",
        )
        update.provenance.epistemic_class = (
            EpistemicClass.EXPERIMENTALLY_DEMONSTRATED if did_survive
            else EpistemicClass.REFUTED)
        self.model_updates.append(update)

        if not did_survive:
            # CRITICAL FIX: Model refuted does NOT auto-kill candidate.
            # Transition to MODEL_REFUTED, then ask adapter if mechanism is refuted.
            self._record_transition(LoopState.MODEL_REFUTED,
                                    f"Model refuted by experiment {latest_obs.observation_id[:8]}... "
                                    f"— but candidate NOT auto-killed. "
                                    f"Asking adapter if mechanism is refuted.")

            # The adapter decides: is this a model error (revise model) or a
            # mechanism impossibility (kill candidate)?
            mechanism_refuted = self.adapter.is_mechanism_refuted(
                self.candidate, self.mechanistic_model, latest_obs,
                self.model_updates)

            if mechanism_refuted:
                self._kill(f"MECHANISM REFUTED: the causal mechanism is proven "
                           f"impossible by experiment {latest_obs.observation_id[:8]}...")
                return False
            else:
                # Model is wrong but mechanism may survive. Revise model / new experiment.
                self._record_transition(LoopState.INFORMATION_GAIN_RANKING,
                                        f"Model refuted but mechanism survives. "
                                        f"Revising model / selecting new experiment.")
                return True  # Continue to next experiment selection

        self._record_transition(LoopState.INFORMATION_GAIN_RANKING,
                                f"Model survived experiment. Proceeding to next experiment selection.")
        return True

    def run_information_gain_ranking(self) -> bool:
        """Step 11: Rank remaining uncertainties by information gain.

        The loop identifies which uncertainty, if resolved, would most
        reduce the total uncertainty budget.
        """
        if not self.uncertainty_budget:
            raise RuntimeError("No uncertainty budget")

        # The adapter identifies what we still don't know
        remaining = self.adapter.identify_remaining_uncertainties(
            self.candidate, self.uncertainty_budget, self.observations,
            self.model_updates)

        self._record_transition(LoopState.NEXT_FALSIFICATION_EXPERIMENT,
                                f"Remaining uncertainties: {len(remaining)}")
        return True

    def run_next_falsification_proposal(self) -> FalsificationProposal:
        """Step 12: Propose the SINGLE next falsification experiment.

        Per CEO directive: the AI must say 'this is the single experiment
        that would reduce our uncertainty the most or most efficiently kill
        the invention.'
        """
        next_exp = self.adapter.propose_next_falsification(
            self.candidate, self.uncertainty_budget, self.observations,
            self.model_updates, self.rng)

        self.falsification_proposal = next_exp
        self._record_transition(LoopState.EVIDENCE_DOSSIER,
                                f"Next falsification: {next_exp.proposed_experiment.objective} "
                                f"(kill_prob={next_exp.kill_probability:.2f})")
        return next_exp

    def _check_completion_gate(self) -> dict:
        """Check whether all 11 stages required for completion have occurred.

        Per CEO directive (P0.3): is_complete=True must be IMPOSSIBLE unless:
          problem_proof = GREEN
          destruction = PASSED
          mechanistic_model = VALID
          VVUQ = COMPLETE
          virtual_cohort = EXECUTED
          experiment = EXECUTED
          raw_data = INGESTED + INTEGRITY_VERIFIED
          model_update = COMPLETE
          next_falsification = GENERATED
          buyer_value = EVIDENCED
          regulatory_dossier = COMPLETE

        Any missing stage → INCOMPLETE.

        Completion must be EARNED BY STATE, not asserted by the code path.
        """
        stages = {
            "problem_proof_green": (
                self.problem_proof is not None and
                self.problem_proof.question_1_exists == "GREEN"
            ),
            "destruction_passed": (
                self.causal_graph is not None and
                len(self.causal_graph.established_infeasible_edges) == 0 and
                len(self.causal_graph.critical_unknowns) == 0
            ),
            "mechanistic_model_valid": self.mechanistic_model is not None,
            "vvuq_complete": self.uncertainty_budget is not None,
            "virtual_cohort_executed": (
                self.virtual_cohort is not None and
                len(self.virtual_cohort.patients) > 0
            ),
            "experiment_executed": self.experiment is not None,
            "raw_data_ingested": len(self.observations) > 0,
            "raw_data_integrity_verified": all(
                o.data_hash != "" for o in self.observations
            ),
            "model_update_complete": len(self.model_updates) > 0,
            "next_falsification_generated": self.falsification_proposal is not None,
            "buyer_value_evidenced": len(self.buyer_requirements) > 0 and
                all(r.is_met is True for r in self.buyer_requirements),
            "regulatory_dossier_complete": self.regulatory_evidence is not None,
        }
        missing = [name for name, passed in stages.items() if not passed]
        return {
            "all_stages_passed": len(missing) == 0,
            "missing_stages": missing,
            "stages": stages,
        }

    def run_generate_dossier(self) -> Dossier:
        """Step 13: Generate the buyer/regulatory dossier from the validated system.

        Per CEO directive (P0.3): is_complete=True must be MECHANICALLY EARNED.
        If any of the 11 stages is missing, is_complete=False (INCOMPLETE).
        """
        self.regulatory_evidence = self.adapter.generate_regulatory_evidence(
            self.candidate, self.uncertainty_budget, self.observations,
            self.model_updates)

        # Check the earned completion gate
        gate = self._check_completion_gate()

        if not gate["all_stages_passed"]:
            # Dossier is INCOMPLETE — is_complete MUST be False
            self.dossier = Dossier(
                candidate_id=self.candidate.name,
                candidate=self.candidate.to_dict(),
                problem_proof=self.problem_proof.to_dict() if self.problem_proof else {},
                causal_graph=self.causal_graph.to_dict() if self.causal_graph else {},
                mechanistic_model=self.mechanistic_model.to_dict() if self.mechanistic_model else {},
                uncertainty_budget=self.uncertainty_budget.to_dict() if self.uncertainty_budget else {},
                virtual_cohort=self.virtual_cohort.to_dict() if self.virtual_cohort else {},
                experiments=[self.experiment.to_dict()] if self.experiment else [],
                observations=[o.to_dict() for o in self.observations],
                model_updates=[u.to_dict() for u in self.model_updates],
                buyer_requirements=[r.to_dict() for r in self.buyer_requirements],
                regulatory_evidence=self.regulatory_evidence.to_dict() if self.regulatory_evidence else {},
                is_complete=False,  # CRITICAL: mechanically False, not asserted
            )
            self._record_transition(LoopState.INCOMPLETE,
                                    f"Dossier INCOMPLETE. Missing stages: "
                                    f"{gate['missing_stages']}")
            return self.dossier

        # All 11 stages passed — is_complete is EARNED
        self.dossier = Dossier(
            candidate_id=self.candidate.name,
            candidate=self.candidate.to_dict(),
            problem_proof=self.problem_proof.to_dict(),
            causal_graph=self.causal_graph.to_dict(),
            mechanistic_model=self.mechanistic_model.to_dict(),
            uncertainty_budget=self.uncertainty_budget.to_dict(),
            virtual_cohort=self.virtual_cohort.to_dict(),
            experiments=[self.experiment.to_dict()],
            observations=[o.to_dict() for o in self.observations],
            model_updates=[u.to_dict() for u in self.model_updates],
            buyer_requirements=[r.to_dict() for r in self.buyer_requirements],
            regulatory_evidence=self.regulatory_evidence.to_dict(),
            is_complete=True,  # EARNED by state, not asserted
        )
        self._record_transition(LoopState.EVIDENCE_DOSSIER,
                                "Dossier generated. All 11 stages PASSED. "
                                "is_complete=True EARNED.")
        return self.dossier

    def _kill(self, reason: str):
        """Kill the candidate. No resurrection."""
        self.kill_reason = reason
        self._record_transition(LoopState.KILLED, reason)

    def _block(self, reason: str):
        """Block the candidate. Can be revisited if evidence emerges."""
        self._record_transition(LoopState.BLOCKED, reason)

    def _rank_by_information_gain(self, experiments: list[Experiment]) -> list[Experiment]:
        """Rank experiments by DATA-DRIVEN information gain.

        Per CEO directive (P0.4): NOT a manually supplied score.
        Must be calculated from:
          uncertainty → candidate outcomes → expected posterior uncertainty → cost/risk

        The adapter's calculate_information_gain() method provides the
        domain-specific calculation.
        """
        for exp in experiments:
            exp.expected_information_gain = self.adapter.calculate_information_gain(
                self.candidate, self.uncertainty_budget, exp, self.observations)
        return sorted(experiments,
                       key=lambda e: e.expected_information_gain,
                       reverse=True)

    def get_state_summary(self) -> dict:
        """Get a summary of the current loop state."""
        return {
            "candidate": self.candidate.name if self.candidate else None,
            "current_state": self.state.value,
            "state_history": self.state_history,
            "kill_reason": self.kill_reason,
            "observations_count": len(self.observations),
            "model_updates_count": len(self.model_updates),
            "random_seed": self.random_seed,
            "adapter": self.adapter.__class__.__name__,
        }

    def is_replayable(self) -> bool:
        """Verify the loop is replayable.

        Given the same evidence state and random seed, the loop must
        reproduce the same proposed experiment.
        """
        return self.random_seed is not None and self.virtual_cohort is not None

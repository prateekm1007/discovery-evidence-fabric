"""End-to-End Invention Loop Engine.

Per Article XXXV (Constitution v1.5.0):
  A completed invention is a closed-loop validated system that can generate
  its own next falsification experiment from new evidence.

One engine, four adapters:
  - R6Adapter (Slot 1: Passive Rescue / Obstruction Bypass)
  - SensingAdapter (Slot 2: Adaptive / Sensing eShunt)
  - TherapeuticAdapter (Slot 3: Controlled CNS Therapeutic)
  - LifecycleAdapter (Slot 4: CNS / Lifecycle Intelligence)

Usage:
    from epistemic_integrity.invention_loop_engine import InventionLoopEngine, R6Adapter

    adapter = R6Adapter()
    engine = InventionLoopEngine(adapter, random_seed=42)
    engine.run_candidate(candidate)
    engine.run_problem_proof()
    engine.run_destruction()
    # ... continue through the loop
"""

from .engine import InventionLoopEngine
from .schemas import (
    # Core types
    Candidate, ProblemHypothesis, CausalGraph, CausalEdge,
    MechanisticModel, Assumption, UncertaintyBudget,
    VirtualCohort, VirtualPatient, Experiment, RawObservation,
    ModelUpdate, FalsificationProposal, BuyerRequirement,
    RegulatoryEvidence, Dossier,
    # Falsifiability + evidence predicates
    FalsifiablePrediction, FalsifiabilityStatus, MechanismRefutationVerdict,
    EvidencePredicate,
    # Enums
    EpistemicClass, EvidenceType, LoopState, ParameterClassification,
    ClassifiedParameter,
    # Provenance
    Provenance,
)
from .adapters.r6_adapter import R6Adapter
from .adapters.sensing_adapter import SensingAdapter
from .adapters.therapeutic_adapter import TherapeuticAdapter
from .adapters.lifecycle_adapter import LifecycleAdapter
from .adapters.base import InventionLoopAdapter

__all__ = [
    "InventionLoopEngine",
    "InventionLoopAdapter",
    "R6Adapter", "SensingAdapter", "TherapeuticAdapter", "LifecycleAdapter",
    "Candidate", "ProblemHypothesis", "CausalGraph", "CausalEdge",
    "MechanisticModel", "Assumption", "UncertaintyBudget",
    "VirtualCohort", "VirtualPatient", "Experiment", "RawObservation",
    "ModelUpdate", "FalsificationProposal", "BuyerRequirement",
    "RegulatoryEvidence", "Dossier",
    "EpistemicClass", "EvidenceType", "LoopState",
    "Provenance",
]

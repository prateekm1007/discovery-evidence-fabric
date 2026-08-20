"""
Bayesian Expected Information Gain (EIG) calculator.

Per CEO directive (2026-08-20, third round):
  Replace count-based entropy with TRUE expected information gain:
    prior distribution over hypotheses
    likelihood of each possible experimental outcome
    posterior distribution
    expected posterior entropy
    EIG = prior_entropy - expected_posterior_entropy

  Then include: EIG / cost / risk / feasibility

  The entire calculation must be auditable.

This module implements EIG using discrete hypothesis distributions
and Bayesian updating. It is NOT a heuristic proxy.

The calculation:
  1. Define a set of mutually exclusive hypotheses H = {h1, h2, ..., hn}
     each with a prior probability P(hi).
  2. For each possible experimental outcome oj:
     a. Compute likelihood P(oj | hi) for each hypothesis.
     b. Compute posterior P(hi | oj) ∝ P(oj | hi) * P(hi).
     c. Compute posterior entropy H(posterior | oj).
  3. Compute expected posterior entropy:
     E[H(posterior)] = Σ P(oj) * H(posterior | oj)
     where P(oj) = Σ P(oj | hi) * P(hi)
  4. EIG = H(prior) - E[H(posterior)]

This is the information-theoretic optimal experiment selection criterion.
"""

from __future__ import annotations

import math
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from uuid import uuid4
from datetime import datetime, timezone
from enum import Enum


class EIGEpistemicClass(str, Enum):
    """The epistemic class of EIG inputs (hypotheses, priors, likelihoods).

    Per CEO directive (2026-08-20, fourth round):
      'Mathematical sophistication does not upgrade the epistemic class of its inputs.'
      A perfectly implemented Bayesian engine fed invented priors is still an
      invention of the coder, not a discovery of reality.

    Every prior probability, outcome likelihood, and hypothesis must carry
    one of these classes. SYNTHETIC_TEST_ONLY cannot influence real experiment selection.
    """
    EVIDENCE_BOUND = "EVIDENCE_BOUND"                # Bound by external evidence (literature, IFU, measurement)
    MODEL_DERIVED = "MODEL_DERIVED"                  # Derived from a physics/computational model
    EXPERIMENTALLY_ESTIMATED = "EXPERIMENTALLY_ESTIMATED"  # Estimated from prior experiments
    EXPERT_PRIOR = "EXPERT_PRIOR"                    # Expert judgment, explicitly labeled
    SYNTHETIC_TEST_ONLY = "SYNTHETIC_TEST_ONLY"      # Synthetic/hypothetical — CANNOT influence real experiments


@dataclass
class EIGProvenance:
    """Provenance for an EIG input (hypothesis, prior, or likelihood).

    Every EIG input must carry:
      source → provenance → epistemic class → uncertainty

    This prevents semantic drift where invented numbers re-enter through
    the Bayesian hypothesis model.
    """
    source: str = ""
    epistemic_class: EIGEpistemicClass = EIGEpistemicClass.SYNTHETIC_TEST_ONLY
    uncertainty: str = ""  # Description of uncertainty in this value
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "epistemic_class": self.epistemic_class.value,
            "uncertainty": self.uncertainty,
            "created_at": self.created_at,
        }


@dataclass
class Hypothesis:
    """A discrete hypothesis about the mechanism.

    Per CEO directive (P0.1 — fourth round):
      Every hypothesis must carry provenance with epistemic class.
      SYNTHETIC_TEST_ONLY hypotheses CANNOT influence real experiment selection.

    For SYNTHETIC_TEST_ONLY hypotheses, use fictional labels (H1, H2, H3, H4),
    NOT real-world values like "3 mmHg" or "5 mmHg" that imply evidence
      the frozen protocol does not provide.
    """
    name: str
    description: str
    prior_probability: float  # Must sum to 1.0 across all hypotheses
    provenance: EIGProvenance = field(default_factory=EIGProvenance)

    def __post_init__(self):
        if self.prior_probability < 0 or self.prior_probability > 1:
            raise ValueError(f"Prior probability {self.prior_probability} out of [0,1] range")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "prior_probability": self.prior_probability,
            "provenance": self.provenance.to_dict(),
        }


@dataclass
class ExperimentalOutcome:
    """A possible experimental outcome with its likelihood under each hypothesis.

    Per CEO directive (P0.1 — fourth round):
      Every likelihood P(outcome | hypothesis) must carry provenance.
      Likelihoods are themselves models — they need source + epistemic class.

    For SYNTHETIC_TEST_ONLY likelihoods, the entire calculation is labeled
    as synthetic and CANNOT influence real experiment selection.
    """
    name: str
    description: str
    # Likelihood P(outcome | hypothesis) for each hypothesis
    likelihoods: dict[str, float]  # hypothesis_name -> probability
    provenance: EIGProvenance = field(default_factory=EIGProvenance)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "likelihoods": self.likelihoods,
            "provenance": self.provenance.to_dict(),
        }


@dataclass
class EIGCalculationTrace:
    """Full audit trace of an EIG calculation.

    Per CEO directive: 'Keep the entire calculation auditable.'
    Every step is recorded so a human can verify the math.

    Per CEO directive (P0.4 — fourth round):
      The trace carries the MINIMUM epistemic class of all inputs.
      If ANY input is SYNTHETIC_TEST_ONLY, the entire calculation is
      SYNTHETIC_TEST_ONLY and CANNOT influence real experiment selection.
    """
    calculation_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hypotheses: list[dict] = field(default_factory=list)
    outcomes: list[dict] = field(default_factory=list)
    prior_entropy: float = 0.0
    posterior_entropies: dict[str, float] = field(default_factory=dict)  # outcome_name -> entropy
    outcome_probabilities: dict[str, float] = field(default_factory=dict)  # outcome_name -> P(o)
    expected_posterior_entropy: float = 0.0
    eig: float = 0.0
    cost: float = 1.0
    risk: float = 1.0
    feasibility: float = 1.0
    eig_per_cost: float = 0.0  # EIG / (cost * risk / feasibility)
    # CRITICAL: the minimum epistemic class of all inputs
    minimum_epistemic_class: EIGEpistemicClass = EIGEpistemicClass.SYNTHETIC_TEST_ONLY
    can_influence_real_experiment: bool = False  # True only if ALL inputs are non-synthetic

    def to_dict(self) -> dict:
        return asdict(self)


class BayesianEIGCalculator:
    """Calculates true Expected Information Gain using Bayesian updating.

    This replaces the count-based heuristic with a proper information-theoretic
    calculation.

    Usage:
        calculator = BayesianEIGCalculator()

        # Define hypotheses with priors
        hypotheses = [
            Hypothesis("h1", "valve opens at 3mmHg", 0.2),
            Hypothesis("h2", "valve opens at 5mmHg", 0.5),
            Hypothesis("h3", "valve opens at 8mmHg", 0.2),
            Hypothesis("h4", "valve never opens", 0.1),
        ]

        # Define possible outcomes with likelihoods
        outcomes = [
            ExperimentalOutcome("o1", "pressure=4.5mmHg",
                               {"h1": 0.7, "h2": 0.2, "h3": 0.01, "h4": 0.0}),
            ExperimentalOutcome("o2", "pressure=8.2mmHg",
                               {"h1": 0.01, "h2": 0.05, "h3": 0.8, "h4": 0.0}),
            ExperimentalOutcome("o3", "no opening at 10mmHg",
                               {"h1": 0.0, "h2": 0.0, "h3": 0.0, "h4": 0.9}),
        ]

        trace = calculator.calculate_eig(hypotheses, outcomes, cost=1.0, risk=1.0, feasibility=1.0)
        print(f"EIG = {trace.eig:.4f}")
    """

    @staticmethod
    def _entropy(probabilities: list[float]) -> float:
        """Calculate Shannon entropy (base 2) of a probability distribution.

        H(p) = -Σ p_i * log2(p_i)

        Handles p_i = 0 gracefully (0 * log(0) = 0).
        """
        entropy = 0.0
        for p in probabilities:
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy

    @staticmethod
    def _normalize_priors(hypotheses: list[Hypothesis]) -> dict[str, float]:
        """Normalize prior probabilities to sum to 1.0."""
        total = sum(h.prior_probability for h in hypotheses)
        if total == 0:
            raise ValueError("Prior probabilities sum to 0 — cannot normalize")
        return {h.name: h.prior_probability / total for h in hypotheses}

    @staticmethod
    def _bayesian_update(
        priors: dict[str, float],
        outcome: ExperimentalOutcome
    ) -> dict[str, float]:
        """Compute posterior P(hypothesis | outcome) using Bayes' theorem.

        P(h | o) = P(o | h) * P(h) / P(o)
        where P(o) = Σ P(o | h) * P(h)
        """
        # Compute marginal probability of outcome P(o)
        p_outcome = 0.0
        for h_name, prior in priors.items():
            likelihood = outcome.likelihoods.get(h_name, 0.0)
            p_outcome += likelihood * prior

        if p_outcome == 0:
            # Outcome is impossible under all hypotheses
            # Return uniform posterior (maximum uncertainty)
            n = len(priors)
            return {h: 1.0 / n for h in priors}

        # Compute posterior
        posteriors = {}
        for h_name, prior in priors.items():
            likelihood = outcome.likelihoods.get(h_name, 0.0)
            posteriors[h_name] = (likelihood * prior) / p_outcome

        return posteriors

    def calculate_eig(
        self,
        hypotheses: list[Hypothesis],
        outcomes: list[ExperimentalOutcome],
        cost: float = 1.0,
        risk: float = 1.0,
        feasibility: float = 1.0
    ) -> EIGCalculationTrace:
        """Calculate Expected Information Gain.

        EIG = H(prior) - E[H(posterior | outcome)]

        where:
          H(prior) = entropy of prior distribution
          E[H(posterior)] = Σ P(o) * H(posterior | o)

        Args:
            hypotheses: List of hypotheses with prior probabilities
            outcomes: List of possible experimental outcomes with likelihoods
            cost: Cost of running the experiment (higher = more expensive)
            risk: Risk of running the experiment (higher = riskier)
            feasibility: Feasibility score (higher = more feasible, 0 = impossible)

        Returns:
            EIGCalculationTrace with full audit trail
        """
        trace = EIGCalculationTrace()
        trace.hypotheses = [h.to_dict() for h in hypotheses]
        trace.outcomes = [o.to_dict() for o in outcomes]
        trace.cost = cost
        trace.risk = risk
        trace.feasibility = feasibility

        # Step 1: Normalize priors
        priors = self._normalize_priors(hypotheses)

        # Step 2: Compute prior entropy
        trace.prior_entropy = self._entropy(list(priors.values()))

        # Step 3: For each outcome, compute posterior and posterior entropy
        expected_posterior_entropy = 0.0

        for outcome in outcomes:
            # Compute marginal P(o) = Σ P(o|h) * P(h)
            p_outcome = sum(
                outcome.likelihoods.get(h_name, 0.0) * prior
                for h_name, prior in priors.items()
            )
            trace.outcome_probabilities[outcome.name] = p_outcome

            # Compute posterior P(h | o)
            posteriors = self._bayesian_update(priors, outcome)

            # Compute posterior entropy H(posterior | o)
            posterior_entropy = self._entropy(list(posteriors.values()))
            trace.posterior_entropies[outcome.name] = posterior_entropy

            # Accumulate expected posterior entropy: E[H(posterior)] = Σ P(o) * H(posterior|o)
            expected_posterior_entropy += p_outcome * posterior_entropy

        trace.expected_posterior_entropy = expected_posterior_entropy

        # Step 4: EIG = H(prior) - E[H(posterior)]
        trace.eig = trace.prior_entropy - expected_posterior_entropy

        # Step 5: EIG per unit cost/risk/feasibility
        # Higher cost → lower value. Higher risk → lower value. Higher feasibility → higher value.
        denominator = (cost * risk) / max(feasibility, 0.001)  # Avoid div by zero
        trace.eig_per_cost = trace.eig / denominator if denominator > 0 else 0.0

        # Step 6 (P0.4 — fourth round): Compute minimum epistemic class
        # If ANY hypothesis or outcome is SYNTHETIC_TEST_ONLY, the entire
        # calculation is SYNTHETIC_TEST_ONLY and CANNOT influence real experiments.
        all_classes = []
        for h in hypotheses:
            all_classes.append(h.provenance.epistemic_class)
        for o in outcomes:
            all_classes.append(o.provenance.epistemic_class)

        # Determine minimum epistemic class
        # SYNTHETIC_TEST_ONLY is the lowest; EVIDENCE_BOUND is the highest
        class_rank = {
            EIGEpistemicClass.SYNTHETIC_TEST_ONLY: 0,
            EIGEpistemicClass.EXPERT_PRIOR: 1,
            EIGEpistemicClass.MODEL_DERIVED: 2,
            EIGEpistemicClass.EXPERIMENTALLY_ESTIMATED: 3,
            EIGEpistemicClass.EVIDENCE_BOUND: 4,
        }
        if all_classes:
            min_rank = min(class_rank.get(c, 0) for c in all_classes)
            trace.minimum_epistemic_class = next(
                c for c, r in class_rank.items() if r == min_rank
            )
        else:
            trace.minimum_epistemic_class = EIGEpistemicClass.SYNTHETIC_TEST_ONLY

        # can_influence_real_experiment = True only if NO input is SYNTHETIC_TEST_ONLY
        trace.can_influence_real_experiment = (
            trace.minimum_epistemic_class != EIGEpistemicClass.SYNTHETIC_TEST_ONLY
        )

        return trace

    def rank_experiments(
        self,
        hypotheses: list[Hypothesis],
        experiment_options: list[dict[str, Any]],
    ) -> list[tuple[str, EIGCalculationTrace]]:
        """Rank multiple experiments by EIG per cost.

        Each experiment_option is a dict with:
          - name: experiment name
          - outcomes: list of ExperimentalOutcome
          - cost: float
          - risk: float
          - feasibility: float

        Returns list of (name, trace) sorted by eig_per_cost descending.
        The FIRST item is the single best experiment to run.
        """
        results = []
        for exp in experiment_options:
            trace = self.calculate_eig(
                hypotheses,
                exp["outcomes"],
                cost=exp.get("cost", 1.0),
                risk=exp.get("risk", 1.0),
                feasibility=exp.get("feasibility", 1.0),
            )
            results.append((exp["name"], trace))

        # Sort by EIG per cost (descending)
        results.sort(key=lambda x: x[1].eig_per_cost, reverse=True)
        return results


def demonstrate_eig():
    """Demonstrate the EIG calculator with a simple R6 example."""
    calc = BayesianEIGCalculator()

    # R6 hypotheses: what is the bypass valve opening pressure?
    hypotheses = [
        Hypothesis("h1", "valve opens at 3mmHg", 0.15),
        Hypothesis("h2", "valve opens at 5mmHg", 0.40),
        Hypothesis("h3", "valve opens at 8mmHg", 0.25),
        Hypothesis("h4", "valve never opens (mechanism fails)", 0.10),
        Hypothesis("h5", "valve opens variably (unreliable)", 0.10),
    ]

    # Experiment A: measure opening pressure at 5mmHg differential
    exp_a_outcomes = [
        ExperimentalOutcome("opens_below_5", "valve opens before 5mmHg",
                           {"h1": 0.9, "h2": 0.3, "h3": 0.01, "h4": 0.0, "h5": 0.3}),
        ExperimentalOutcome("opens_at_5_to_8", "valve opens 5-8mmHg",
                           {"h1": 0.1, "h2": 0.6, "h3": 0.2, "h4": 0.0, "h5": 0.3}),
        ExperimentalOutcome("opens_above_8", "valve opens above 8mmHg",
                           {"h1": 0.0, "h2": 0.1, "h3": 0.7, "h4": 0.0, "h5": 0.2}),
        ExperimentalOutcome("no_opening", "valve does not open",
                           {"h1": 0.0, "h2": 0.0, "h3": 0.09, "h4": 1.0, "h5": 0.2}),
    ]

    # Experiment B: test at 3mmHg differential
    exp_b_outcomes = [
        ExperimentalOutcome("opens_at_3", "valve opens at 3mmHg",
                           {"h1": 0.9, "h2": 0.05, "h3": 0.0, "h4": 0.0, "h5": 0.2}),
        ExperimentalOutcome("no_opening_at_3", "valve does not open at 3mmHg",
                           {"h1": 0.1, "h2": 0.95, "h3": 1.0, "h4": 1.0, "h5": 0.8}),
    ]

    experiments = [
        {"name": "Experiment A: test at 5mmHg", "outcomes": exp_a_outcomes,
         "cost": 1.0, "risk": 0.5, "feasibility": 1.0},
        {"name": "Experiment B: test at 3mmHg", "outcomes": exp_b_outcomes,
         "cost": 1.0, "risk": 0.5, "feasibility": 1.0},
    ]

    ranked = calc.rank_experiments(hypotheses, experiments)

    print("=" * 60)
    print("BAYESIAN EIG DEMONSTRATION (R6 Example)")
    print("=" * 60)
    print()
    print(f"Prior entropy: H(prior) = {calc.calculate_eig(hypotheses, exp_a_outcomes).prior_entropy:.4f} bits")
    print()
    print("Ranked experiments (by EIG per cost):")
    for name, trace in ranked:
        print(f"  {name}")
        print(f"    EIG = {trace.eig:.4f} bits")
        print(f"    Expected posterior entropy = {trace.expected_posterior_entropy:.4f} bits")
        print(f"    EIG/cost = {trace.eig_per_cost:.4f}")
        print(f"    Outcome probabilities: {trace.outcome_probabilities}")
        print()

    print(f"BEST EXPERIMENT: {ranked[0][0]}")
    print(f"  EIG = {ranked[0][1].eig:.4f} bits")
    print(f"  This is the experiment that maximally reduces uncertainty.")


if __name__ == "__main__":
    demonstrate_eig()

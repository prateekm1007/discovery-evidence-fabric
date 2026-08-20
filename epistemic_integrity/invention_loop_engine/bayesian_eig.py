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


@dataclass
class Hypothesis:
    """A discrete hypothesis about the mechanism.

    Example for R6:
      h1: "bypass valve opens at 3 mmHg" (prior=0.2)
      h2: "bypass valve opens at 5 mmHg" (prior=0.5)
      h3: "bypass valve opens at 8 mmHg" (prior=0.2)
      h4: "bypass valve never opens"    (prior=0.1)
    """
    name: str
    description: str
    prior_probability: float  # Must sum to 1.0 across all hypotheses

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExperimentalOutcome:
    """A possible experimental outcome with its likelihood under each hypothesis.

    Example for R6:
      outcome: "measured opening pressure = 4.5 mmHg"
      likelihoods: {h1: 0.8, h2: 0.15, h3: 0.01, h4: 0.0}
      (h1 predicts ~3mmHg, so 4.5 is close; h2 predicts 5, so 4.5 is close too;
       h3 predicts 8, so 4.5 is far; h4 predicts never, so 0.0)
    """
    name: str
    description: str
    # Likelihood P(outcome | hypothesis) for each hypothesis
    likelihoods: dict[str, float]  # hypothesis_name -> probability

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EIGCalculationTrace:
    """Full audit trace of an EIG calculation.

    Per CEO directive: 'Keep the entire calculation auditable.'
    Every step is recorded so a human can verify the math.
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

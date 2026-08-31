# ADR-R378-01 — THE FIDELITY LADDER (Progressive Evaluation Architecture)

**Status:** ACCEPTED (CEO audit implementation item 1, 2026-08-31)
**Decision record for:** the A2/discovery pipeline and the R378
Technical Improvement Engine
**Implementing code:** `discovery_fabric/engine/evaluator_contract.py`
(declared tiers + evidence ranks), `discovery_fabric/engine/
improvement_engine.py` (the escalation budget)
**Constitutional anchors:** Art. XXVII (thresholds declared with
provenance), Art. XXXIV (reality as the bottleneck — spend compute
only where it resolves real uncertainty), Art. XXXVIII (evidence ranks
1–5; the ladder cannot manufacture rank-5 evidence)

---

## Context

The CEO's second-pass research audit (2026-08-31) identified the
fidelity ladder as a first-class architectural concept missing from all
prior Toscanini documentation:

> "Cheap model → more detailed model → expensive simulation → physical
> experiment is standard in aerospace and automotive design (it is
> explicitly how NASA uses CFD) and has never appeared in any Toscanini
> documentation. It belongs in the engine architecture as a
> first-class concept. The implication is significant: not every
> invention candidate deserves a full A2 pipeline run. A fast
> low-fidelity filter can screen candidates before the expensive
> multi-source discovery, adversarial attack, and prior art runs. This
> could reduce compute cost per candidate by an order of magnitude at
> scale."

R377 had already produced the screenable signal without naming it: the
I1–I5 invention-quality dimensions are a cheap, deterministic,
network-free measurement that predicts which candidates deserve
expensive downstream work (the SPAN_UNDERIVED ineligibility rule is a
fidelity-ladder decision wearing different clothes).

## Decision

Toscanini adopts a DECLARED fidelity ladder as architecture. Every
evaluation of a candidate happens at the **least expensive evaluator
tier capable of resolving the current uncertainty**, escalating only
when the cheaper tier's verdict is genuinely undecidable.

```
TIER 0  TERM_RULE              deterministic term-rule diagnostics
                                 (I1–I5 instrument, span derivation,
                                 attack verdicts) — network-free,
                                 <1 s, ALWAYS runs first
TIER 1  STRUCTURED_CONSTRAINT  structured constraint checking against
                                 declared constraint models (future)
TIER 2  NUMERICAL_SOLVER       deterministic physics/chemistry solvers
                                 (analytical equations, ODE/PDE where
                                 cheap) — future
TIER 3  SIMULATION             domain simulators (FEM/CFM/kinetics) and
                                 NEURAL_OPERATOR surrogates (the MIT
                                 NeuralOperator library is the
                                 integration point) — future, OPT-IN
TIER 5  EXPERIMENT             physical measurement — REALITY. Not
                                 registrable by software (Art. XXXVIII);
                                 reached only through the reality
                                 boundary, never simulated
```

### The rules (mechanical, not aspirational)

1. **Tier 0 is unconditional.** Every candidate — naive, grid, ensemble,
   and every improvement-engine MUTATION — is measured at tier 0 before
   anything more expensive touches it. (Implemented: the improvement
   loop's diagnose step; the grid's span-derivation check; the
   survivor-selection ineligibility rule.)
2. **Escalation is budgeted, not default.** Declared thresholds
   (Art. XXVII, in `IMPROVEMENT_THRESHOLDS`): MAX_ITERATIONS_DEFAULT 2,
   MAX_PROPOSALS_PER_ITERATION 3, and the metered-source guards
   (PatentBear reserve floor; Lens politeness window). Expensive tiers
   are opt-in per call — never a silent upgrade of the diagnostic
   baseline (a simulator registering later does NOT displace
   TermRuleEvaluator as the default).
3. **Every tier declares its evidence rank.** TERM_RULE → 3 (AI_
   INFERENCE-class output), NUMERICAL_SOLVER / SIMULATION /
   NEURAL_OPERATOR → 4 (COMPUTATIONAL_RESULT), EXPERIMENT → 5
   (PHYSICAL_OBSERVATION — structurally unregistrable in software; the
   ladder's terminal rung is reality itself).
4. **The ladder never manufactures rank.** A higher tier's output
   enters the chain with its own class; no tier's verdict promotes a
   lower tier's claim (Art. XXVIII). The decisive experiment selected
   at the end of the loop is a PLAN for tier 5, not a claim about it.
5. **Screening kills are honest kills.** A candidate eliminated at tier
   0 (SPAN_UNDERIVED, KILLED-by-attack premise) is recorded with the
   measured reason; the pipeline does not silently requeue it for a
   costlier tier to "give it another chance" (Art. XX — falsification
   before optimization).

## What this changes in the A2 pipeline

Nothing retroactively; the existing stage order already embodies a
procedural ladder (cheap LLM grid → attack → metered search → quality
gate → experiment selection). This ADR makes the ladder DECLARED and
gives the improvement engine a contract to escalate within:

```
CANDIDATE
  → TIER 0 diagnose (always)
  → mutation proposals validated at TIER 0 (deterministic gates)
  → full re-evaluation (re-adjudication at search-evidence tier)
  → keep/kill on measured improvement
  → [future] escalate surviving candidates to TIER 2/3 evaluators
    registered behind evaluator_contract.register_evaluator()
  → decisive experiment (TIER 5 plan; EIG-ranked)
```

## Consequences

- **Cost:** candidates that cannot survive tier 0 never reach metered
  patent searches or LLM attack windows. Measured this cycle: the
  improvement pass's proposal budget (3/iteration) and the PatentBear
  reserve floor are the first two live instances of ladder economics.
- **Auditability:** every evaluation artifact records which tier
  produced it (`evaluator_id`, `fidelity_tier`, `evidence_rank` on
  every EvaluatorDiagnosis; `collision_mode` LIVE/REPLAY_CACHE on
  re-adjudications).
- **Future integration:** a NeuralOperator-backed evaluator or an
  AU-style physics model plugs in at tier 3 WITHOUT changing any
  consumer — the CEO's integration posture (ADR companion note in
  TECHNICAL_IMPROVEMENT_ENGINE_DIRECTIVE.md §2).
- **Known limits (honest):** tiers 1–3 have no implementations yet;
  the ladder is architecture + economics + contract now, physics
  later. The EXPLICIT anti-goal stands: no giant physics foundation
  model (CEO "DO NOT" list; Art. XX problem-existence — the unproven
  claim is the loop, not the model).

## References

- CEO second-pass audit (2026-08-31) — fidelity-ladder directive.
- PINO (arXiv:2111.03794) — constraint-aware evaluation pattern.
- Catheter inverse design (Science Advances 2024) — the full-loop
  reference demonstration.
- NeuralOperator (MIT-licensed) — the tier-3 integration point.
- EPISTEMIC_CONSTITUTION.md Art. XXVII/XXXIV/XXXVIII.

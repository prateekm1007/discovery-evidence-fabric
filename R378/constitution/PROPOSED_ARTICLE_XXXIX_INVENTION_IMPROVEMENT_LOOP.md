# PROPOSED ARTICLE XXXIX — THE INVENTION IMPROVEMENT LOOP

**Status:** PROPOSED — awaiting CEO ratification (constitution
amendment v1.8.0 → v1.9.0). This document records the CEO's 2026-08-31
constitutional analysis in ratifiable article form. The Coder does not
amend the Constitution unilaterally; the CEO's message was advisory
prose ("I would add..."), and this is the vehicle for turning it into
law.
**Ratification evidence appended:** the R378 Technical Improvement
Engine already mechanically enforces the core of this article — the
proposed text below is a description of RUNNING CODE, not aspiration
(see the mapping table in §4).

---

## 1. The proposed article text

> ### Article XXXIX — The Invention Improvement Loop
>
> A technology candidate is not complete merely because it survives
> discovery, evidence, or prior-art analysis. A candidate is a
> HYPOTHESIS about a technology that must be improved, attacked, and
> re-evaluated.
>
> **The loop:** DIAGNOSE → MUTATE → RE-EVALUATE → COMPARE → KEEP/KILL
> → REPEAT, executed where technically justified on every surviving
> candidate.
>
> **Every mutation must have:**
> 1. a documented reason for mutation;
> 2. a diagnostic or evidence basis;
> 3. a preserved parent candidate;
> 4. a precise description of what changed;
> 5. independent re-evaluation;
> 6. provenance linking parent → diagnostic → mutation → child;
> 7. a measurable or otherwise defensible reason for considering the
>    child superior.
>
> **The system shall not optimize merely for internal scores.** A
> candidate shall not be considered improved solely because an
> evaluator score increased; where possible, improvement must be
> explained causally in technical terms. The generator shall never
> modify the evaluator, its thresholds, or its evidence rules in order
> to obtain a higher candidate score.
>
> **If no defensible improvement can be generated, the system shall be
> permitted and encouraged to kill the candidate.** A higher kill rate
> is acceptable when it increases the credibility of surviving
> technology packages. The objective is not maximum candidate survival;
> the objective is maximum credible technological value.

## 2. The supporting principles the CEO proposed (recorded verbatim in
summary)

1. **Directional Improvement** — every surviving candidate should have
   an identified direction of improvement, not merely a pass.
2. **Candidate Lineage** — no mutation becomes an orphaned invention;
   what changed, why, and what evidence caused the change.
3. **Improvement Must Be Causal** — not "I 0.56 → 0.71" but "I1
   improved because the mechanism is now supported by the span."
4. **Evaluator Independence** — the generator may respond to criticism;
   it may never rewrite the critic.
5. **No Score-Chasing** — better technology, not higher internal
   scores (R377 proved Q=STRONG can coexist with weak substance).
6. **Minimum Necessary Complexity** — the least expensive evaluator
   capable of resolving the current uncertainty (the fidelity ladder).
7. **Escalating Fidelity** — surviving increasingly serious attacks
   requires increasingly physically faithful evidence.
8. **Reality Separation** — OBSERVED / MEASURED / CALCULATED /
   SIMULATED / MODEL-DERIVED / INFERRED / HYPOTHESIZED / PROPOSED /
   UNKNOWN; never silently upgraded.
9. **Falsification Before Optimization** — kill test first, then
   improve.
10. **Cross-Domain Transfer** — same + adjacent + distant domain
    search under strict evidence requirements.
11. **Novelty Is Not Enough** — technically meaningful, not merely
    different from retrieved prior art.
12. **Kill Quality** — a system that kills weak inventions accurately
    is more valuable than one that produces many survivors.
13. **The Decisive Next Information** — "What information would most
    change our belief about this invention?" then the cheapest
    credible way to obtain it (EIG machinery, with MODEL_DERIVED priors
    never treated as empirical probabilities).

## 3. The demotions the CEO proposed (recorded)

- Excessive procedural specificity (files, registries, scripts,
  instrumentation structures) → engineering standards; the Constitution
  says WHAT must be true, not HOW it is currently implemented.
- Source-count thinking → sufficient evidence diversity and depth to
  resolve the invention question.
- Patent-centric thinking → patents are one evidence class among the
  full network ("We are not running a patent court" — the standing CEO
  rule since Toscanini's naming).
- Dossier completeness as a major success criterion → a packaging
  requirement, not an invention-quality criterion.
- Static candidate thinking → the terminal sequence becomes
  candidate → diagnose → improve → attack → improve → evaluate →
  package.

## 4. Ratification evidence — what R378 already enforces mechanically

| Proposed principle | R378 enforcement (code, measured) |
|---|---|
| The loop itself | `improvement_engine.improve_candidate`: DIAGNOSE → PROPOSE → VALIDATE → APPLY → RE-EVALUATE → KEEP/KILL → REPEAT with directional feedback |
| Mutation reason + basis | `mutation_block.diagnostic_trigger` (dimension, measured_before, basis) + `fields_changed` |
| Preserved parent | parent spec hash on every child; the parent artifact stays on disk untouched |
| Lineage provenance | the causal chain `ORIGINAL -> DIAGNOSTIC -> MUTATION -> NEW CANDIDATE` (Art. XXXVIII schema: before_hash / after_hash / trigger / reason / timestamp) + `_improvement.history` |
| Independent re-evaluation | span re-measured; coverage re-adjudicated (REPLAY_CACHE/LIVE); BOTH instruments re-run; no inherited scores (CEO rule 11) |
| Evaluator independence | the LLM only proposes; deterministic gates decide; the Q instrument is hash-pinned (Art. XXX pin test); the I instrument is pinned-additive by test |
| No score-chasing | untriggered/off-target mutations structurally rejected (rule 8); flag-driven weaknesses require the FLAG CLEARED, not marginal score movement |
| Negatives never erased | mechanical parent→child preservation check (rule 10) |
| Falsification before optimization | the Art. XX guard: attack-KILLED candidates are never improved |
| Kill quality | honest outcome vocabulary incl. KILLED_NO_DEFENSIBLE_MUTATION; a KILL verdict blocks packaging (rule 9); w7 live demonstration ended in an honest kill |
| Fidelity ladder | `evaluator_contract` declared tiers + budget thresholds (ADR-R378-01) |
| Reality separation | every evaluator declares its evidence rank; EXPERIMENT tier is structurally unregistrable |

## 5. What is NOT yet enforced (honest gaps, for the ratification
record)

- Principles 2/7's full strength: only TERM_RULE-tier evaluators exist;
  the escalating-fidelity rungs (numerical/simulation/NeuralOperator)
  are contract-reserved, not implemented.
- Principle 13's full ambition: the EIG machinery exists but priors are
  MODEL_DERIVED (disclosed); the improvement loop targets diagnosed
  weaknesses, not yet the maximal-information-next-question.
- The demotions (§3) are policy-level; they would require a v1.9.0
  redraft pass over Articles carrying implementation specifics — a
  separate ratification step from this article.

## 6. CEO ratification checklist (per the constitution's own amendment
history)

1. Ratify Article XXXIX as §1 (or return it with edits).
2. Decide the five-pillar architecture (EPISTEMIC / DISCOVERY /
   INVENTION integrity + REALITY BRIDGE) as the v1.9.0 organizing
   scheme, or keep the flat article list.
3. Decide whether the §3 demotions authorize a redraft cycle (the
   Coder recommends: YES but as its own round, after the patent-source
   redundancy build — the redraft touches every article and must not
   be rushed).
4. The Coder's standing position: no constitutional change weakens any
   existing article; every new principle is added with its mechanical
   enforcement named (§4) or its gap disclosed (§5).

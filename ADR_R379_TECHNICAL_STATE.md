# ADR R379 — STRUCTURED TECHNICAL STATE + TECHNICAL EVALUATOR CONTRACT

**Status:** IMPLEMENTED (R379, CEO directive 2026-08-31 — TECHNICAL
IMPROVEMENT ENGINE V2)
**Sponsor:** CEO R379 directive — "make the mutation engine increasingly
about THE TECHNOLOGY, not merely the wording of the technology."
**Constitution:** v1.8.0 (read in full before this ADR was written)

## Context

R378 closed the epistemic improvement loop (DIAGNOSE → PROPOSE →
VALIDATE → APPLY → RE-EVALUATE → KEEP/KILL), measured I 0.560 → 0.728
on the six-survivor replay. The CEO's audit identified the next
weakness precisely: the engine can mutate the REPRESENTATION of the
invention better than the TECHNICAL REALITY of it. Mutations rewrite
mechanism prose; they do not yet move design variables.

## Decision

Three additive layers, no existing layer weakened:

1. **`engine/technical_state.py` — the structured technical state.**
   A first-class machine model of the technology with the ten CEO
   categories: OBJECTS, PARAMETERS, GEOMETRY, MATERIALS, OPERATING
   CONDITIONS, CONSTRAINTS, OBJECTIVES, FAILURE MODES, DEPENDENCIES,
   MEASURABLE OUTPUTS. Every value carries an explicit epistemic class:
   - `EXTRACTED` — the value is bound to a VERBATIM span of custodied
     evidence (number must appear inside the span; Art. II/VI).
   - `MODELLED` — a declared design proposal, never promoted (Art. XXVIII).
   - `UNKNOWN` — legitimate gap; never zero, never mutated against
     (Art. XXV).
   The state is proposed by the LLM (untrusted, Art. XVIII) and
   admitted piece-by-piece by DETERMINISTIC validation; invalid pieces
   are dropped to UNKNOWN with recorded reasons — honest degradation,
   never fatal, never silent.

2. **`engine/technical_evaluator.py` — the technical evaluator
   contract.** Input: technical state + constraints + objective +
   evidence. Output: predicted behavior (direction-level at the
   analytical tier), constraint results (SATISFIED / VIOLATED /
   UNVERIFIABLE), sensitivity map, limiting variable, improvement
   directions, uncertainty record, computation log (Art. XXXVIII).
   First live implementation: `analytical_monotone_v1` — deterministic
   sign propagation over the dependency graph at STRUCTURED_CONSTRAINT
   tier (evidence rank 3: its outputs are MODEL-class inferences, and
   every one is labeled as such — never a measurement). Numeric
   constraint checking is computed where values and limits exist.
   Higher tiers (NUMERICAL_SOLVER, SIMULATION, NEURAL_OPERATOR — rank
   4) are contract-reserved and opt-in; EXPERIMENT (rank 5) remains
   structurally unregistrable (the reality boundary).

3. **`engine/technical_improvement_engine.py` — the V2 mutation loop.**
   CANDIDATE → TECHNICAL DIAGNOSE (limiting variable + direction) →
   PROPOSE (LLM untrusted) → VALIDATE (deterministic: the change must
   target the named limiting variable, in the evaluator's predicted
   improving direction, within the declared envelope — an UNBOUNDED
   parameter is not mutable, because any "improvement" on it would be
   unconstrained invention) → APPLY (child state + spec-text sync + the
   Art. XXXVIII causal chain) → INDEPENDENT RE-EVALUATION (fresh
   technical evaluation + prior-art re-adjudication + both instruments;
   nothing inherited) → KEEP/KILL → SECOND IMPROVEMENT.
   Every KEEP records an IMPROVEMENT ATTRIBUTION:
   technical mechanism → changed variable → direction → predicted
   effect → evaluated result → evidence class.
   KEEP is NOT granted for a score increase: the child must be
   predicted-technically-better (objective direction) with constraints
   preserved, negatives preserved, no new structural flags, prior-art
   position not degraded, and the mechanism still evidence-derived.

## Anti-gaming properties (declared before implementation)

- **Unbounded parameters are immutable** — no declared envelope ⇒ no
  quantitative mutation (prevents inventing favorable magnitudes).
- **Value-class persistence** — EXTRACTED survives only with a
  verified span; MODELLED is declared on the child; nothing converts
  UNKNOWN → value without a recorded class.
- **Spec-text sync gate** — a technical mutation that does not carry
  the change into the mechanism/intervention text is rejected (the
  state and the prose may not diverge).
- **Constraint wall kill** — improving directions that all violate
  declared constraints end in an honest kill, not a wording mutation.
- **Fidelity escalation is honest** — escalate only when the deciding
  question is unresolved at the current tier AND a higher tier is
  registered; today that means the ledger records
  `escalation_needed: true, next_tier_available: false`.

## What this is NOT

- Not a physics foundation model (CEO item 10 — interface only).
- Not a measurement: analytical predictions are rank-3 model
  inferences; numerical results would be rank-4 with computation logs;
  rank 5 stays reality's alone.
- Not a replacement of the R378 epistemic loop: the pipeline runs the
  epistemic pass FIRST (wording), then the technical pass (design) —
  strictness is additive.

## Measured consequences (recorded in R379 artifacts)

- **Controlled replay, six R378 survivors** (TOSCANINI/R379_TECHNICAL_REPLAY):
  6/6 TECHNICAL_UNQUANTIFIED — the honest 🟡 state measured per
  candidate. The extraction layer works (5–10 parameters admitted per
  candidate; rail-steel got 2 evidence-proven envelopes), but these
  candidates' own evidence carries no connected
  envelope+objective+leverage. Recorded, never a kill, never faked.
- **Live production integration** (ENGINE_RUNS/w9_..., full engine run,
  fresh domain): the composed pipeline ran live in production order —
  epistemic pass IMPROVED, technical pass TECHNICAL_UNQUANTIFIED
  (honest), package P-158 HELD_FOR_HUMAN_REVIEW (grid-origin
  discipline). ENGINE_RUNS/w8_... (fresh domain): epistemic kill
  honestly blocked packaging before the technical layer engaged —
  correct composition (a killed candidate produces no package).
- **Live positive path** (TOSCANINI/R379_TECHNICAL_LIVE_POSITIVE/
  M1_m1_t03_pedicle_screw_fracture_a1718560): the full CEO milestone
  demonstrated LIVE on a real M1 campaign candidate with its own
  custodied evidence:
  DIAGNOSE (limiting variable C_FIBER_CONTENT/param_2, objective
  MAXIMIZE) → TECHNICAL MUTATION (None → 55.0, MODELLED, INCREASE) →
  INDEPENDENT TECHNICAL EVALUATION ("CONFIRMED ... with constraints
  preserved") → KEEP → SECOND IMPROVEMENT (55.0 → 65.0) → KEEP.
  Both KEEPs carry improvement attributions with evidence class
  AI_INFERENCE rank 3 ("NOT a measurement"); the child spec carries
  the two-mutation causal chain with parent hashes, and the
  numerical-provenance audit PASSes on it (MODELLED values
  OK_CLASSIFIED, the one EXTRACTED value span-verified OK).
- **Two live defects found and fixed during measurement** (each pinned
  by adversarial tests):
  1. Sign inversion on direct MINIMIZE objectives (the first draft
     proposed INCREASING the target of a MINIMIZE objective).
  2. K4 conflated the epistemic and technical layers: it rejected a
     technically-CONFIRMED mutation for I1 numeric movement (0.125 →
     0.071, both already below the structural floor). Refined: the
     gate now blocks only the floor crossing (derived → underived);
     numeric movement is recorded, never gated (CEO R379 item 8).

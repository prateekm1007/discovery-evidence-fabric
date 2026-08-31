# ADR R383 — The Analytical Equation Layer (quantitative technical evaluator)

**Status:** ACCEPTED (CEO R383 directive: "IMPROVE THE INVENTION ENGINE")
**Date:** 2026-09-01
**Supersedes:** nothing (additive to R379/R380; the R379 monotone evaluator
and the R380 CAD pipeline keep their exact semantics)

## The decision

Add a DETERMINISTIC ANALYTICAL EQUATION LAYER to the technical improvement
engine: an engine-owned registry of closed-form engineering relations
(Hagen–Poiseuille laminar flow, residence time, hydrostatic head, hoop
stress, acoustic reflection, capacitive sensing, PV irradiance, osmotic
flux, piezoelectric energy bound), a deterministic BINDING engine that
binds a candidate's structured technical state to those equations, and a
quantitative evaluator (`analytical_equation_v1`, fidelity tier
`ANALYTICAL_EQUATION`, evidence rank 4 = COMPUTATIONAL_RESULT) that
computes objective values, margins, numeric sensitivities, and
mutation proposals by closed-form/bisection solve.

## Why

The R379 evaluator is direction-only (sign propagation over declared
MONOTONE relations). It can say "increasing the lumen diameter improves
flow"; it cannot say "flow is 12.7 mL/h against a 20 mL/h requirement —
margin −36% — and the diameter that closes it is 0.344 mm". The CEO R383
milestone requires Candidate B to be *technically better for a stated
reason*, mutations to operate on real technical variables with
measured consequences, and 3D geometry to change when a relevant design
variable changes — then feed MEASURED geometry back into evaluation.
That requires magnitudes from deterministic physics BEFORE any
expensive simulation (CEO focus 5/6: analytical equations, geometric
calculations, simple numerical models, domain-specific constraints —
explicitly NOT a giant physics model).

## Architecture

```
technical_state (R379)  ──┐
parametric model         ──┼──> bind_equations() ──> evaluate_quantitatively()
measurements (R380, CAD) ──┘       (deterministic)         │
                                                            ├─ objective value + margin
                                                            ├─ elasticity sensitivities
                                                            ├─ magnitude-ranked limiting variable
                                                            └─ solve_for (bisection over the envelope)
```

1. **Equation registry** (`technical_equations.py`). Each equation
   declares: id, domain, symbolic form, input roles with acceptable
   units + aliases, output role, monotonicity sign per input, validity
   predicates (VERIFIED / VIOLATED / UNDECIDABLE), compute function
   (SI units internally; conversions declared), and provenance class:
   `ANALYTICAL_LAW` (conservation-derived closed form) or
   `ANALYTICAL_ESTIMATE` (engineering estimate with declared empirical
   coefficient). Equations are ENGINE-OWNED code (like CAD templates) —
   the LLM never writes them (Art. XVIII).

2. **Constants table.** A small declared set of reference values (CSF
   viscosity, water density, gravity…) each with epistemic class
   `ENGINEERING_REFERENCE`, source note, and uncertainty. A constant is
   used ONLY when the candidate's own state does not declare the
   quantity; every use is recorded in the computation log. A declared
   state value always wins.

3. **Binding engine** (deterministic, fail-closed). For each equation ×
   state: each input role is resolved to a state parameter by exact unit
   match + deterministic keyword scoring on
   param_id/name/role text; ties are ambiguity and DO NOT bind. Values
   resolve in the order GEOMETRY_MEASURED (the candidate's own validated
   parametric model, R380 loop order) > EXTRACTED > MODELLED >
   ENGINEERING_REFERENCE constant; unresolved ⇒ binding inactive.
   **Sign agreement gate:** when the state declares a direct dependency
   between a bound input and the bound output, the declared direction
   must agree with the equation's monotonicity; a disagreement REJECTS
   the binding (`STATE_PHYSICS_DISAGREEMENT` — a real diagnostic
   finding: the state's declared physics contradicts the analytical
   law; never resolved by preference, Art. II).

4. **Validity discipline (Art. IV fail-closed).** A computation runs
   only when every validity predicate is decidable and VERIFIED (e.g.
   Poiseuille requires laminar Re < 2300 and L/D ≥ 10 — Re computed from
   the same resolved inputs; if an input is missing the check is
   UNDECIDABLE ⇒ no number is emitted). VIOLATED and UNDECIDABLE are
   recorded with reasons; they never produce values.

5. **Quantities and classes.** Every computed output is
   `COMPUTATIONAL_RESULT` (rank 4) with a computation log listing every
   input, its source (state-EXTRACTED / state-MODELLED /
   GEOMETRY_MEASURED / ENGINEERING_REFERENCE), the SI conversion
   applied, the equation form, and the validity verdicts. Inputs'
   classes are preserved — MODELLED never becomes MEASURED, and the
   state is NEVER written back to (Art. XXVIII). Geometry-measured
   inputs are used *in preference to* declared values (the built solid
   is the design reality at this tier) with any declared-vs-measured
   discrepancy recorded, never silently resolved.

6. **Margins and the keep gate (K8, additive).** The objective margin is
   the normalized distance of the computed objective value from the
   binding constraint on the objective target (direction-consistent;
   absent ⇒ margin UNBOUNDED and the quantitative layer does not drive
   mutations). `keep_or_kill_technical` gains K8: when BOTH parent and
   child carry a quantitative objective computation from the same bound
   equation, the child's margin must improve by at least the declared
   non-trivial fraction (`QUANT_MIN_RELATIVE_IMPROVEMENT`); otherwise
   the mutation is REJECTed with the measured margin comparison as the
   reason. Candidates without bindings are untouched (K1 direction
   criterion governs). K1–K7 are unchanged.

7. **Deterministic mutation proposals (R383).** When the quantitative
   layer finds an unmet requirement, it solves (bisection over the
   declared envelope — every library equation is monotone in each
   input, declared in the registry) for the design-variable value that
   reaches limit × (1 + `SOLVE_MARGIN_FACTOR`). The proposal enters the
   production gates through the SAME path as LLM proposals
   (`validate_technical_mutation` T0–T10 — deterministic proposals get
   NO exemption) and its provenance is recorded as
   `DETERMINISTIC_SOLVE` rather than an untrusted LLM. When the solve
   is unreachable inside the envelope, the diagnosis records
   `UNREACHABLE_IN_ENVELOPE` with the best-achievable value and margin —
   measured evidence for the kill reason. T1's
   `target_is_limiting_variable` gate is NOT weakened: the trigger
   evaluation legitimately comes from the higher-tier evaluator when
   the quantitative layer is bound (the ordinal convention of R379
   remains the trigger for unbound candidates).

8. **Post-loop honesty.** If keeps occurred but the final quantitative
   margin is still negative and the solve is unreachable in the
   envelope, the outcome is `KILLED_CONSTRAINT_WALL` with the measured
   best-achievable margin (CEO rule 10: a candidate that cannot be
   defensibly improved to its requirement is killed).

## Declared thresholds (Art. XXVII)

| Threshold | Value | Class | Justification |
|---|---|---|---|
| `QUANT_MIN_RELATIVE_IMPROVEMENT` | 0.005 (0.5% of \|limit\|) | ENGINEERING | below half a percent of the binding limit, margin movement is computation-noise-level at this tier, not a defensible improvement |
| `SOLVE_MARGIN_FACTOR` | 0.10 | ENGINEERING | solving exactly onto the boundary leaves zero robustness; a 10% design margin is the declared convention for proposal generation (the T-gates and K-gates still decide) |
| Bisection iterations | 60 (tolerance 1e-9 relative) | ENGINEERING | deterministic solve convergence for monotone relations; the tolerance is 3+ orders below any declared engineering margin |

## Epistemic risks and mitigations

- **Art. XXX (never optimize the evaluator):** equations are standard
  analytical relations with declared provenance — none were tuned to
  make a specific candidate pass. The sign-agreement gate can only
  REJECT bindings. Adversarial tests attack the margin computation
  (validity violations, ambiguous bindings, forged inputs).
- **Art. XXVII (no threshold invention):** all three thresholds above
  are declared with class and justification before any computation uses
  them; the constants table carries per-value provenance.
- **Art. XXVIII / XXXVIII:** outputs are rank-4 COMPUTATIONAL_RESULTs
  with logs; no physical observation is claimed anywhere; validity is
  checked, and when undecidable the layer emits nothing.
- **Art. IV (no fallback):** a VIOLATED or UNDECIDABLE validity
  predicate blocks the number. There is no "compute anyway and hope".
- **Art. VII (never weaken the verifier):** T0–T10 and K1–K7 are
  byte-identical; K8 is strictly additional and only engages when both
  sides carry quantitative records from the same equation.
- **Art. IX (certification is observational):** the quantitative
  evaluation never writes to the state, the spec, or the model; it
  returns records only (tests pin no-write-back).

## What this is NOT

- Not a simulation stack (no FEM/CFD; the SIMULATION tier remains
  unregistered).
- Not a physical validation: every number is a model prediction under
  declared assumptions with declared input classes.
- Not a portfolio-packaging change: the buyer portfolio is untouched;
  this is the core invention machine (per the CEO directive to stop
  spending effort on portfolio bookkeeping).

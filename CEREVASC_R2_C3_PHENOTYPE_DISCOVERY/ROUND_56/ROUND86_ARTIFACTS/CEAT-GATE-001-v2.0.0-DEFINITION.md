# CONSTITUTIVE-EQUIVALENCE-AND-TANGENT GATE (CEAT-GATE-001)
## Renamed from CE-GATE-001 per CEO Round 86 directive

**Version:** 2.0.0
**Renamed from:** CE-GATE-001 v1.1.0
**Date:** 2026-08-23
**Round:** 86
**Authority:** CEO Round 85 deep audit directive:

> "I would actually rename the current CE-GATE: CONSTITUTIVE-EQUIVALENCE-AND-TANGENT GATE and make the hard invariant: W_A = W_B, P_A = P_B, C_A = C_B over the frozen deformation domain."

---

## The Hard Invariant

A cross-solver L3 comparison is permitted ONLY when, for every deformation
state F in the frozen benchmark deformation domain D:

```
W_A(F) = W_B(F)        (strain-energy density equivalence)
P_A(F) = P_B(F)        (first Piola-Kirchhoff stress equivalence)
C_A(F) = C_B(F)        (consistent material tangent equivalence)
```

All three must hold simultaneously. **Matching stress at a single state
is NOT sufficient.** Matching energy and stress without matching tangent
is NOT sufficient. The full chain energy → first derivative → second
derivative must be equivalent.

This is the operationalization of the principle:

> "The machine is not allowed to declare two models equivalent because
> their outputs look similar. It must prove that they implement the
> same mathematics."

---

## Why all three levels?

Each level catches a different class of subtle solver differences:

| Level | What it tests | Failure mode caught |
|-------|---------------|---------------------|
| W (energy) | strain-energy density function | Different SED forms (e.g., (ln J)² vs (J-1)²) |
| P (1st PK stress) | first derivative of W | Stress law bugs, wrong stress measure, sign errors |
| C (tangent) | second derivative of W | Tangent bugs, finite-difference noise, material vs consistent tangent confusion, BFGS contamination |

A solver can pass W and P but fail C if:
- It uses a numerical Jacobian with too-large finite-difference step
- It uses a different tangent formulation (material vs consistent)
- It has a tangent implementation bug that produces correct stress but wrong slope
- It uses a quasi-Newton approximation (BFGS) that has not converged to the true tangent

This is why the gate is named CONSTITUTIVE-EQUIVALENCE-AND-TANGENT, not
just CONSTITUTIVE-EQUIVALENCE.

---

## Check Structure (8 checks, v2.0.0)

The 8 checks from v1.1.0 are retained, but their semantics are tightened:

| # | Check | What must be TRUE |
|---|-------|------------------|
| 1 | strain_energy_density | W_A(F) = W_B(F) for all F in D (character-by-character formula match) |
| 2 | stress_law | P_A(F) = P_B(F) for all F in D (analytical formula match) |
| 3 | tangent_equivalence | C_A(F) = C_B(F) for all F in D (analytical formula match + numerical verification at 5 states) |
| 4 | compressibility_formulation | The mathematical formulation (mixed u-p vs pure displacement penalty) must produce IDENTICAL W, P, C over D — not just "similar stress at one state". Either prove equivalence or keep RED. **NO "acceptable caveat" category allowed.** |
| 5 | parameter_mapping | E,ν → μ,K mapping is exact and identical |
| 6 | stress_measure | Both solvers output the same stress measure (Cauchy OR 2nd PK OR 1st PK). If different, the push-forward / pull-back transformation must be DERIVED, APPLIED, and VERIFIED INDEPENDENTLY at multiple deformation states — not just one. |
| 7 | quadrature | Same integration rule (e.g., 2×2×2 Gauss for hex8) |
| 8 | reference_configuration | Same formulation (TL or UL) |

---

## The "No Acceptable Caveat" Rule

Per CEO Round 85:

> "I would not accept 'acceptable caveat' yet. This is exactly the kind
> of language that can turn a real mathematical difference into an
> informal exception. You need to prove one of:
> A. equivalent constitutive response under the benchmark, or
> B. the two formulations converge to the same continuum solution under
>    the specific boundary conditions, with the distinction explicitly
>    documented. Until then: CE-GATE-001 = REFUSE."

**Operationalization:** Check #4 (compressibility_formulation) has only
two valid values: `true` (equivalence proven) or `false` (equivalence
not proven). The values `"acceptable_caveat"`, `"similar_at_benchmark"`,
`"documented_difference"`, etc. are ALL interpreted as `false` by the
gate. There is no third state.

If the mixed u-p and pure displacement formulations cannot be proven
equivalent over the benchmark deformation domain, the gate stays RED
indefinitely. The L3 comparison cannot proceed until either:
- (a) Both solvers use the same formulation type (e.g., both pure displacement with the same penalty)
- (b) Mathematical proof of equivalence is supplied
- (c) A new benchmark version (B004, B005, ...) is frozen with a formulation both solvers natively support identically

---

## Multi-State Verification Requirement

Per CEO Round 85:

> "the gate should not turn green until the transformation is
> independently verified across multiple deformation states."

For checks #2 (stress_law), #3 (tangent_equivalence), and #6
(stress_measure), the audit must include verification at **at least 5
deformation states** spanning the benchmark deformation domain:

| State | λ_z | ε_zz |
|-------|-----|------|
| S0 | 1.000 | 0% (small-strain consistency check) |
| S1 | 1.025 | 2.5% |
| S2 | 1.050 | 5.0% |
| S3 | 1.075 | 7.5% |
| S4 | 1.100 | 10.0% (benchmark final state) |

At each state, the audit must report:
- Solver A's output value (with residual/convergence status)
- Solver B's output value (with residual/convergence status)
- Analytical reference value
- Relative differences (A vs analytical, B vs analytical, A vs B)

A single-state agreement is NOT sufficient to pass checks #2, #3, #6.

---

## Implementation Notes

- The gate script (`constitutive_equivalence_gate.py`) is updated to v2.0.0
- The "acceptable_caveat" string is explicitly listed in the
  `evaluate_check()` function as a FAIL value
- The audit JSON schema requires a `multi_state_verification` block for
  checks #2, #3, #6 — audits without it are REFUSED

---

## Inheritance from v1.1.0

All artifacts produced under v1.1.0 remain valid for historical
reference. The v2.0.0 gate is stricter:
- "acceptable_caveat" → FAIL (was implicitly accepted)
- Single-state verification → INSUFFICIENT (must be 5+ states)
- Tangent check #3 now requires analytical formula match + numerical verification (was numerical only)

Audits created under v1.1.0 must be re-evaluated under v2.0.0 before
being used for any L3 attempt.

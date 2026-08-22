# Round 88 — Evidence State Taxonomy and Custom Tangent Implementation

**Author:** CTO mode, Round 88
**Date:** 2026-08-23
**Purpose:** Per CEO Round 87 directives:
1. Override `tan_mod_function` for the custom log-J term (the actual Newton-used tangent)
2. Define evidence-state taxonomy (DERIVED → IMPLEMENTED → NUMERICALLY_VERIFIED → SOLVER_INTEGRATED → CROSS_SOLVER_VERIFIED)
3. Freeze L3-BENCHMARK-005 BEFORE any solver execution
4. Make loading-path check quantitative (frozen thresholds, not just qualitative shape)
5. Add domain coverage to CEAT gate

---

## 1. Evidence-State Taxonomy (machine-readable)

Per CEO Round 87:

> "The gate should never report PASS when only the derivative has been validated. Use explicit states: DERIVED → IMPLEMENTED → NUMERICALLY_VERIFIED → SOLVER_INTEGRATED → CROSS_SOLVER_VERIFIED."

These states apply to each of the 9 CEAT-GATE-001 checks. A check is TRUE (PASS) only when its evidence state is CROSS_SOLVER_VERIFIED. Anything less is an explicit non-passing state.

| State | Meaning | Example (for check #3 tangent_equivalence) |
|-------|---------|---------------------------------------------|
| `NOT_STARTED` | No work done yet | Tangent not derived |
| `DERIVED` | Analytical derivation exists on paper/file | Log-J tangent derived (Round 86) |
| `IMPLEMENTED` | Code exists implementing the derivation | Custom `tan_mod_function` written (Round 88) |
| `NUMERICALLY_VERIFIED` | Implementation output matches analytical at multiple states | `term_mode='tan_mod'` extraction matches analytical at 5 states (Round 88) |
| `SOLVER_INTEGRATED` | Newton solver actually uses this implementation | Confirmed by inspecting SfePy's Newton iteration matrix (Round 88) |
| `CROSS_SOLVER_VERIFIED` | Both solvers (A and B) reach SOLVER_INTEGRATED for this check | FEBio tangent also extracted and matches at 5 states (requires FEBio rebuild, Round 89) |

A check is TRUE only at CROSS_SOLVER_VERIFIED. All lower states are explicit non-passing.

---

## 2. Custom Tangent Implementation for log-J Volumetric SED

### 2.1 The wrong inherited tangent (BulkPenaltyTLTerm)

From SfePy source `terms_hyperelastic.c`, function `dq_tl_he_tan_mod_bulk`:

```c
cbulk21 = K * J * (J - 1);   // for W_vol = (K/2)(J-1)^2
cbulk22 = K * J * J;          // for W_vol = (K/2)(J-1)^2
pd[sym*ir+ic] = (cbulk21 + cbulk22) * invC[ir] * invC[ic]
              - cbulk21 * (invC2_ikjl[ir,ic] + invC2_iljk[ir,ic]);
```

This implements the tangent for `W_vol = (K/2)(J-1)²`, NOT `(K/2)(ln J)²`.

### 2.2 The correct log-J tangent

For `W_vol = (K/2)(ln J)²`:
- `S_vol = K * ln(J) * C⁻¹` (corrected in Round 86)
- The material tangent is: `∂S_vol_ij/∂C_kl = K · [(1/2) C⁻¹_kl · C⁻¹_ij - ln(J) · C⁻¹_ik · C⁻¹_lj]`

In Voigt 6×6 notation (symmetric tensors):
```
D_vol[Voigt(i,j), Voigt(k,l)] = K · [(1/2) C⁻¹_kl C⁻¹_ij - ln(J) · sym(C⁻¹_ik C⁻¹_lj)]
```

where `sym(M_ikjl) = (1/2)(M_ikjl + M_iljk)` accounts for the symmetry of C.

Comparing to the wrong (penalty) tangent:
- Wrong: `(K*J*(J-1) + K*J²) · C⁻¹_ij C⁻¹_kl - K*J*(J-1) · (C⁻¹_ik C⁻¹_jl + C⁻¹_il C⁻¹_jk)`
- Correct log-J: `(K/2) · C⁻¹_ij C⁻¹_kl - K*ln(J) · (C⁻¹_ik C⁻¹_jl + C⁻¹_il C⁻¹_jk)`

The structure is similar but the coefficients are different.

### 2.3 Implementation

I will override `tan_mod_function` in the custom SfePy term with a Python function that computes the correct log-J tangent.

---

## 3. L3-BENCHMARK-005 Freeze (BEFORE any solver execution)

Per CEO Round 87:

> "B005 is not merely a technical convenience. It is a new scientific benchmark and must be frozen before either solver is run. Its analytical solution must also be derived independently. Do not create B005 now and then tune it until FEBio and SfePy agree."

B005 will be frozen with 10 fields (the 9 from B002/B004 plus a new `domain_path_coverage` field per CEO directive).

The analytical reference for B005 is the SAME as B004 (since B005 uses the same constitutive law `(K/2)(ln J)²` in pure displacement form). However, B005 must be frozen as a distinct benchmark with its own freeze record, NOT silently inherit B004's reference.

---

## 4. Quantitative Loading-Path Metrics (frozen thresholds)

Per CEO Round 87:

> "Use a pre-registered trajectory metric such as normalized max error / integrated relative error."

I will define:

| Metric | Definition | Frozen Threshold |
|--------|------------|------------------|
| `max_normalized_trajectory_error` | `max_t |sigma_solver(t) - sigma_analytical(t)| / |sigma_analytical(t)|` | < 1% |
| `integrated_normalized_trajectory_error` | `∫ |sigma_solver(t) - sigma_analytical(t)| / |sigma_analytical(t)| dt / ∫ dt` | < 0.5% |
| `max_tangent_trajectory_error` | `max_t |C_solver(t) - C_analytical(t)| / |C_analytical(t)|` | < 2% |
| `integrated_tangent_trajectory_error` | `∫ |C_solver(t) - C_analytical(t)| / |C_analytical(t)| dt / ∫ dt` | < 1% |

These thresholds are frozen BEFORE any solver execution on B005.

---

## 5. Domain Coverage

Per CEO Round 87:

> "the coder's five tangent states need to cover the actual deformation path and neighborhood used by the solver."

B005 specifies:
- Loading path: λ_z ∈ [1.000, 1.100] sampled at 11 points (1.000, 1.010, 1.020, ..., 1.100)
- Tangent verification at all 11 points (not just 5)
- Trajectory shape verification (monotonicity, curvature) at all 11 points

This is `domain_path_coverage`: the frozen deformation domain is the closed interval [1.000, 1.100], sampled at 11 equally-spaced points. Both solvers must be verified at ALL 11 points, not a subset.

---

## 6. Round 88 Execution Plan

1. Define evidence-state taxonomy (this file).
2. Implement custom `tan_mod_function` for log-J in SfePy.
3. Verify the custom tangent by extracting it via `term_mode='tan_mod'` at 5 deformation states.
4. Compare extracted tangent against analytical tangent (Round 86 values).
5. Confirm Newton solver uses the custom tangent (SOLVER_INTEGRATED state).
6. Independently derive analytical reference for B005 (same as B004, but documented as B005's own).
7. Freeze L3-BENCHMARK-005 with 10 fields (including domain_path_coverage).
8. Update CEAT-GATE-001 to v2.2.0 with:
   - Evidence-state taxonomy
   - Quantitative loading-path metrics
   - Domain coverage requirement
9. Re-audit and document honest state.

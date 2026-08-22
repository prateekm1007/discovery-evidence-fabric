# Round 87 — Analytical Consistent Material Tangent for Log-J Volumetric SED

**Author:** CTO mode, Round 87
**Date:** 2026-08-23
**Purpose:** Per CEO Round 86 directive: "Derive the consistent material tangent analytically from W(J) = (K/2)(ln J)². Then verify it three ways: analytical derivation ↔ independent numerical differentiation ↔ finite-difference response of the implementation. Do not count one derivation twice."

This file derives the consistent material tangent for the log-J volumetric
SED `W_vol = (K/2)(ln J)²`, both in 4th-order tensor form and in the
scalar projection `d(σ_zz)/d(λ_z)` that is used by the tangent-equivalence
check.

---

## 1. Setup (recap)

- Volumetric SED: `W_vol(J) = (K/2)(ln J)²`
- Deformation: `F = diag(λ_t, λ_t, λ_z)`, `λ_z` prescribed, `λ_t` free
- Lateral-contraction equation: `σ_xx = 0` (free lateral)
- 1st PK stress (volumetric): `P_vol = (K ln J) F⁻ᵀ` (standard result for log-J)
- 2nd PK stress (volumetric): `S_vol = K ln J · C⁻¹`

---

## 2. The consistent material tangent

The consistent material tangent is the 4th-order tensor:

```
C = ∂P/∂F = ∂²W/∂F²
```

Or equivalently in 2nd PK form (which is what SfePy's `tan_mod_function`
returns):

```
C_S = ∂S/∂C = 2 ∂²W/∂C²  (4th-order tensor)
```

For diagonal F, the only non-zero components are the diagonal-diagonal
ones: `C_iiii` and the cross-terms `C_iijj`. For a uniaxial test, the
relevant projection is:

```
d(σ_zz)/d(λ_z) at fixed lateral-contraction BC
```

This is what I derived in Round 86 (L3-BENCHMARK-004-TANGENT-VERIFICATION).
The derivation there used the chain rule + implicit differentiation of
the lateral-contraction equation.

But that derivation computed `dσ_zz/dλ_z` as a SCALAR derivative that
includes both the partial-derivative contribution AND the implicit
`dJ/dλ_z` contribution. For the implementation's tangent check, we need
the MATERIAL tangent `∂S/∂C` (or `∂P/∂F`), which is the derivative
holding the BCs fixed but treating F as the independent variable.

**Critical distinction:**
- `dσ_zz/dλ_z` (Round 86 derivation): total derivative along the BC-constrained path. Includes `dJ/dλ_z` from the lateral-contraction equation.
- `∂S/∂C` (material tangent): partial derivative at fixed F. This is what the Newton solver uses.

For the tangent-equivalence check, we want to compare the MATERIAL tangent
at each deformation state, NOT the path-following derivative. The path-
following derivative is checked separately by the loading-path equivalence
(new check #9).

---

## 3. Material tangent for log-J volumetric SED

### 3.1 2nd PK stress

```
S_vol = K ln(J) C⁻¹
```

### 3.2 4th-order material tangent ∂S/∂C

The derivative of `S_vol = K ln(J) C⁻¹` with respect to `C`:

```
∂S_vol_ij/∂C_kl = K · ∂/∂C_kl [ln(J) C⁻¹_ij]
                = K · [(∂ln J/∂C_kl) C⁻¹_ij + ln(J) (∂C⁻¹_ij/∂C_kl)]
```

Using the standard identities:
- `∂J/∂C = (J/2) C⁻¹` (so `∂ln J/∂C = (1/2) C⁻¹`)
- `∂C⁻¹_ij/∂C_kl = -C⁻¹_ik C⁻¹_lj` (note: symmetric in i↔j and k↔l)

```
∂S_vol_ij/∂C_kl = K · [(1/2) C⁻¹_kl · C⁻¹_ij - ln(J) C⁻¹_ik C⁻¹_lj]
```

### 3.3 Voigt notation (symmetric 6×6)

For 3D symmetric tensors, Voigt notation maps (11, 22, 33, 12, 23, 13)
to indices (0, 1, 2, 3, 4, 5). The 6×6 material tangent for the
volumetric part:

```
C_vol[Voigt(i,j), Voigt(k,l)] = K · [(1/2) C⁻¹_kl C⁻¹_ij - ln(J) C⁻¹_ik C⁻¹_lj]
```

For diagonal F = diag(λ_t, λ_t, λ_z), `C⁻¹ = diag(1/λ_t², 1/λ_t², 1/λ_z²)`:

```
C_vol[0,0] = K [(1/2)(1/λ_t²)(1/λ_t²) - ln(J)(1/λ_t²)(1/λ_t²)]
           = (K/λ_t⁴) [1/2 - ln(J)]

C_vol[2,2] = K [(1/2)(1/λ_z²)(1/λ_z²) - ln(J)(1/λ_z²)(1/λ_z²)]
           = (K/λ_z⁴) [1/2 - ln(J)]

C_vol[0,2] = C_vol[2,0] = K [(1/2)(1/λ_z²)(1/λ_t²) - ln(J)(1/λ_t²)(1/λ_t²)]
           ... wait, this needs care because C⁻¹_ik depends on which indices
```

Let me redo this more carefully. For the (1,1,1,1) component:

```
∂S_vol_11/∂C_11 = K [(1/2) C⁻¹_11 C⁻¹_11 - ln(J) C⁻¹_11 C⁻¹_11]
                = K C⁻¹_11² [1/2 - ln(J)]
                = (K/λ_t⁴) [1/2 - ln(J)]
```

For the (3,3,3,3) component (z-direction):

```
∂S_vol_33/∂C_33 = K [(1/2) C⁻¹_33 C⁻¹_33 - ln(J) C⁻¹_33 C⁻¹_33]
                = (K/λ_z⁴) [1/2 - ln(J)]
```

For the (1,1,3,3) cross-component:

```
∂S_vol_11/∂C_33 = K [(1/2) C⁻¹_33 C⁻¹_11 - ln(J) C⁻¹_13 C⁻¹_31]
                = K [(1/2)(1/λ_z²)(1/λ_t²) - 0]   (since C⁻¹ is diagonal, C⁻¹_13 = 0)
                = K/(2 λ_t² λ_z²)
```

For the (3,3,1,1) cross-component:

```
∂S_vol_33/∂C_11 = K [(1/2) C⁻¹_11 C⁻¹_33 - ln(J) C⁻¹_31 C⁻¹_13]
                = K/(2 λ_t² λ_z²)
```

So the symmetric 6×6 material tangent for the volumetric part is:

```
C_vol = K · 
| (1/λ_t⁴)[1/2 - ln J]    1/(2λ_t⁴)[1/2 - ln J]·...   1/(2λ_t²λ_z²)        0       0       0   |
| ...                       (1/λ_t⁴)[1/2 - ln J]       1/(2λ_t²λ_z²)        0       0       0   |
| 1/(2λ_t²λ_z²)             1/(2λ_t²λ_z²)              (1/λ_z⁴)[1/2 - ln J] 0       0       0   |
| 0                         0                          0                     ...     0       0   |
| 0                         0                          0                     0       ...     0   |
| 0                         0                          0                     0       0       ... |
```

(The off-diagonal shear-shear blocks involve more terms but are zero for
diagonal F.)

### 3.4 Scalar projection for uniaxial z-tension

For the tangent-equivalence check, we compare the scalar:

```
d(σ_zz)/d(λ_z) at fixed lateral-contraction BC
```

This is the TOTAL derivative along the BC-constrained path, which I
already derived in Round 86 (L3-BENCHMARK-004-TANGENT-VERIFICATION).
The values at 5 states are:

| State | λ_z | dσ_zz/dλ_z (analytical) |
|-------|-----|-------------------------|
| S0 | 1.000 | 0.999999 |
| S1 | 1.025 | 0.974532 |
| S2 | 1.050 | 0.950451 |
| S3 | 1.075 | 0.927594 |
| S4 | 1.100 | 0.905821 |

These are already verified against `scipy.misc.derivative` numerical
differentiation (max 0.0001% diff).

### 3.5 What "three-way verification" means per CEO directive

The CEO demands:

> "verify it three ways:
>   analytical derivation
>   ↔ independent numerical differentiation
>   ↔ finite-difference response of the implementation.
> Do not count one derivation twice."

The three ways are:

1. **Analytical derivation**: the chain-rule + implicit differentiation I did in Round 86.
2. **Independent numerical differentiation**: `scipy.misc.derivative` on `σ_zz(λ_z)` — also done in Round 86, agreed to 0.0001%.
3. **Finite-difference response of the IMPLEMENTATION**: run the SfePy custom term at two nearby deformation states (λ_z ± δ) and compute (σ_zz(λ_z+δ) - σ_zz(λ_z-δ)) / (2δ). This tests the IMPLEMENTATION, not just the math.

**Steps 1 and 2 were done in Round 86. Step 3 is the new contribution for Round 87.**

For step 3 to be meaningful, the SfePy custom term must be run at multiple
deformation states (5 states), and the finite-difference tangent from
the implementation must be compared against the analytical tangent.

This is exactly what the multi-state verification requires, and it tests
the implementation independently of the analytical derivation.

---

## 4. Verification plan for Round 87

1. Re-derive the analytical tangent at 5 states (DONE in Round 86).
2. Re-verify against scipy.misc.derivative (DONE in Round 86, 0.0001% agreement).
3. Run the SfePy custom term at 5 deformation states (NEW in Round 87).
4. Compute finite-difference tangent from SfePy outputs at each state (NEW).
5. Compare finite-difference tangent vs analytical tangent at each state (NEW).
6. If agreement < 1%: tangent equivalence PASS for SfePy side.

For FEBio: same procedure, but FEBio binary must be rebuilt first.

---

## 5. The custom SfePy term's tangent implementation

The current `dw_tl_bulk_logJ_correct` term INHERITS the tangent function
from `BulkPenaltyTLTerm` (its parent class). That inherited tangent is for
the `(K/2)(J-1)²` SED, NOT for `(K/2)(ln J)²`. This is the gap identified
in Round 86.

**Two options for fixing this:**

**Option X (full fix):** Override `tan_mod_function` in the custom class
with a Python function that implements the correct log-J tangent derived
above. This requires the function to match SfePy's internal API for
tangent functions, which is non-trivial.

**Option Y (workaround):** Bypass the inherited tangent by using
SfePy's Newton solver with `eps_r = 1.0` (effectively disabling the
relative residual check) and `i_max = 100` (more iterations). The Newton
solver will use the WRONG tangent (inherited from BulkPenaltyTLTerm),
which means it may converge slowly or not at all for large strains. But
for small strains (10% in our benchmark), it may still converge to the
correct stress.

**Option Z (preferred for verification):** Run the SfePy custom term at
multiple deformation states with a SMALL prescribed displacement, and
compute the finite-difference tangent from the stress outputs. This
gives an empirical measurement of the implementation's actual tangent,
regardless of what the inherited `tan_mod_function` says. Compare this
empirical tangent against the analytical tangent.

Round 87 uses Option Z for verification (because it tests the
IMPLEMENTATION, not the math), and documents Option X as future work
(because the Newton solver currently uses the wrong tangent internally,
which is a separate issue from the verification).

**Important caveat:** Option Z verifies the STRESS produced by the
implementation, which depends on the constitutive law but not on the
tangent function. The tangent function only affects the Newton PATH,
not the converged solution (assuming convergence is achieved). So if
the implementation converges, the stress is correct regardless of the
tangent function. The empirical finite-difference tangent of the stress
output therefore tests the STRESS equation, not the TANGENT equation.

**To test the TANGENT equation itself**, we would need to either:
- (a) Override `tan_mod_function` (Option X) and extract the tangent via `term_mode='tan_mod'`
- (b) Use a different verification method

For Round 87, we document this distinction clearly: the finite-difference
tangent of the stress output verifies the STRESS equation (which we
already verified in Round 86 to 0.004%). The TANGENT equation
verification requires Option X and is left for Round 88.

This is HONEST reporting per Article I (evidence precedes assertion):
we do not claim tangent-equivalence PASS based on stress-output
verification alone.

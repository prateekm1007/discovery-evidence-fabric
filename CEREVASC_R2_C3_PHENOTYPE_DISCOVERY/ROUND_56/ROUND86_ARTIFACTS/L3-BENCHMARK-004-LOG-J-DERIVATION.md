# L3-BENCHMARK-004 — Log-J Volumetric SED Analytical Derivation

**Author:** CTO mode, Round 86
**Date:** 2026-08-23
**Purpose:** Per CEO Round 85 directive: "Finish the log-J tangent properly. Derive: (1) W(J), (2) P(J), (3) consistent material tangent, (4) spatial/Cauchy tangent if that is what the comparison uses. Then verify analytical vs numerical tangent over the same five states."

This file derives the **full constitutive chain** for the log-J volumetric
SED `W_vol = (K/2)(ln J)²`:
1. Strain-energy density W(F)
2. First Piola-Kirchhoff stress P(F) = ∂W/∂F
3. Second Piola-Kirchhoff stress S(F) = 2 ∂W/∂C (intermediate)
4. Cauchy stress σ(F) = (1/J) F P(F) = (1/J) F S(F) F^T
5. Consistent material tangent C = ∂P/∂F = ∂²W/∂F∂F
6. Spatial tangent c = (1/J) F · C · F^T (push-forward of C)

For each, the derivation is given for:
- The deviatoric neo-Hookean part (standard, matches both FEBio and SfePy)
- The volumetric log-J part (the new formulation we want to verify)
- The total (deviatoric + volumetric)

Then the analytical tangent is computed at 5 deformation states and
verified against numerical differentiation.

---

## 1. Setup (frozen in L3-BENCHMARK-002/003)

- Geometry: unit cube, uniaxial z-tension
- F = diag(λ_t, λ_t, λ_z) with λ_z prescribed, λ_t free
- Material parameters: μ = 0.3846, K = 0.8333 (from E=1, ν=0.3)
- Volumetric SED: W_vol = (K/2)(ln J)²
- Deviatoric SED: W_dev = (μ/2)(Ī₁ - 3)
- Lateral-contraction equation: σ_xx = 0 (free lateral)

---

## 2. W(F) — Strain-Energy Density

For F = diag(λ_t, λ_t, λ_z):

```
J = det(F) = λ_t² · λ_z
C = Fᵀ F = diag(λ_t², λ_t², λ_z²)
tr(C) = 2λ_t² + λ_z²
Ī₁ = J^(-2/3) · tr(C) = (λ_t² λ_z)^(-2/3) · (2λ_t² + λ_z²)
```

**Deviatoric:**
```
W_dev = (μ/2)(Ī₁ - 3) = (μ/2)[(λ_t² λ_z)^(-2/3)(2λ_t² + λ_z²) - 3]
```

**Volumetric (log-J):**
```
W_vol = (K/2)(ln J)² = (K/2)(ln(λ_t² λ_z))² = (K/2)(2 ln λ_t + ln λ_z)²
```

**Total:**
```
W = W_dev + W_vol
```

---

## 3. P(F) — First Piola-Kirchhoff Stress

P = ∂W/∂F. For diagonal F, P is diagonal:
```
P_diag = ∂W/∂λ_diag
```

So:
```
P_xx = ∂W/∂λ_t  (since λ_x = λ_t)
P_yy = ∂W/∂λ_t  (since λ_y = λ_t)
P_zz = ∂W/∂λ_z
```

### Compute ∂W/∂λ_t

```
∂W/∂λ_t = ∂W_dev/∂λ_t + ∂W_vol/∂λ_t

W_dev = (μ/2)[(λ_t² λ_z)^(-2/3)(2λ_t² + λ_z²) - 3]

Let A = (λ_t² λ_z)^(-2/3) and B = (2λ_t² + λ_z²).
∂A/∂λ_t = (-2/3)(λ_t² λ_z)^(-5/3) · 2λ_t · λ_z = (-4/3) λ_t λ_z (λ_t² λ_z)^(-5/3)
∂B/∂λ_t = 4λ_t

∂W_dev/∂λ_t = (μ/2)[∂A/∂λ_t · B + A · ∂B/∂λ_t]
            = (μ/2)[(-4/3) λ_t λ_z (λ_t² λ_z)^(-5/3)(2λ_t² + λ_z²)
                   + (λ_t² λ_z)^(-2/3) · 4λ_t]
            = 2μ λ_t (λ_t² λ_z)^(-2/3) - (2μ/3) λ_t λ_z (λ_t² λ_z)^(-5/3)(2λ_t² + λ_z²)
```

```
W_vol = (K/2)(2 ln λ_t + ln λ_z)²

∂W_vol/∂λ_t = (K/2) · 2(2 ln λ_t + ln λ_z) · (2/λ_t)
            = (2K/λ_t)(2 ln λ_t + ln λ_z)
            = (2K/λ_t) · ln J
```

### Compute ∂W/∂λ_z

```
∂A/∂λ_z = (-2/3)(λ_t² λ_z)^(-5/3) · λ_t² = (-2/3) λ_t² (λ_t² λ_z)^(-5/3)
∂B/∂λ_z = 2λ_z

∂W_dev/∂λ_z = (μ/2)[∂A/∂λ_z · B + A · ∂B/∂λ_z]
            = (μ/2)[(-2/3) λ_t² (λ_t² λ_z)^(-5/3)(2λ_t² + λ_z²)
                   + (λ_t² λ_z)^(-2/3) · 2λ_z]
            = μ λ_z (λ_t² λ_z)^(-2/3) - (μ/3) λ_t² (λ_t² λ_z)^(-5/3)(2λ_t² + λ_z²)
```

```
∂W_vol/∂λ_z = (K/2) · 2(2 ln λ_t + ln λ_z) · (1/λ_z)
            = (K/λ_z)(2 ln λ_t + ln λ_z)
            = (K/λ_z) · ln J
```

### Full P

```
P_xx = P_yy = 2μ λ_t (λ_t² λ_z)^(-2/3) - (2μ/3) λ_t λ_z (λ_t² λ_z)^(-5/3)(2λ_t² + λ_z²) + (2K/λ_t) ln J

P_zz = μ λ_z (λ_t² λ_z)^(-2/3) - (μ/3) λ_t² (λ_t² λ_z)^(-5/3)(2λ_t² + λ_z²) + (K/λ_z) ln J
```

---

## 4. S(F) — Second Piola-Kirchhoff Stress (intermediate)

S = 2 ∂W/∂C = F⁻¹ P. For diagonal F:
```
S_ii = P_ii / λ_i
```

So:
```
S_xx = P_xx / λ_t = 2μ (λ_t² λ_z)^(-2/3) - (2μ/3) λ_z (λ_t² λ_z)^(-5/3)(2λ_t² + λ_z²) + (2K/λ_t²) ln J

S_zz = P_zz / λ_z = μ (λ_t² λ_z)^(-2/3) - (μ/3) λ_t² (λ_t² λ_z)^(-5/3)(2λ_t² + λ_z²)/λ_z + (K/λ_z²) ln J
```

Using C^{-1} = diag(1/λ_t², 1/λ_t², 1/λ_z²), the standard form is:
```
S = μ J^(-2/3) [I - (1/3) tr(C) C⁻¹] + (K ln J / J) C⁻¹
```

The volumetric part `S_vol = (K ln J / J) C⁻¹` gives:
```
S_vol_xx = (K ln J / J) · (1/λ_t²) = K ln J / (λ_t² · J) = K ln J / (λ_t⁴ λ_z)

Hmm, wait. Let me recheck. J = λ_t² · λ_z, so:
S_vol_xx = (K ln J / J) · (1/λ_t²) = K ln J / (λ_t² · λ_t² · λ_z) = K ln J / (λ_t⁴ λ_z)
```

That doesn't simplify nicely. Let me check the algebra:
- J = λ_t² · λ_z
- C⁻¹_xx = 1/λ_t² (since C_xx = λ_t²)
- So S_vol_xx = (K ln J / J) / λ_t² = K ln J / (J · λ_t²) = K ln J / (λ_t⁴ · λ_z)

But from P_xx / λ_t, we have:
- P_xx_vol = (2K/λ_t) ln J
- S_xx_vol = P_xx_vol / λ_t = 2K ln J / λ_t² = 2K ln J / λ_t²

There's a factor of 2 discrepancy. Let me recheck the W_vol derivative.

W_vol = (K/2)(ln J)² where J = λ_t² · λ_z
ln J = 2 ln λ_t + ln λ_z
∂(ln J)/∂λ_t = 2/λ_t
∂(ln J)/∂λ_z = 1/λ_z

W_vol = (K/2)(ln J)²
∂W_vol/∂λ_t = (K/2) · 2(ln J) · (2/λ_t) = (2K ln J)/λ_t  ✓
∂W_vol/∂λ_z = (K/2) · 2(ln J) · (1/λ_z) = (K ln J)/λ_z  ✓

S_xx = P_xx / λ_t (for diagonal F, since S = F⁻¹ P, S_ii = P_ii / λ_i)
S_xx_vol = P_xx_vol / λ_t = (2K ln J / λ_t) / λ_t = 2K ln J / λ_t²

But the standard formula gives S_vol = (K ln J / J) C⁻¹, so:
S_vol_xx = (K ln J / J) / λ_t² = K ln J / (λ_t² · J) = K ln J / (λ_t² · λ_t² · λ_z) = K ln J / (λ_t⁴ λ_z)

These don't match. There's a factor of 2 discrepancy. Let me reconsider.

Actually, looking more carefully: W_vol = (K/2)(ln J)², and dW/dJ = K ln J / J.

The standard derivation: S_vol = 2 ∂W_vol/∂C = 2 · (∂W_vol/∂J) · (∂J/∂C)

∂J/∂C = (J/2) C⁻¹ (this is a standard identity)

So S_vol = 2 · (K ln J / J) · (J/2) C⁻¹ = K ln J · C⁻¹

Wait, that gives S_vol = K ln J · C⁻¹, not (K ln J / J) C⁻¹.

Let me redo this. W_vol = (K/2)(ln J)².
∂W_vol/∂J = K ln J · (1/J) = (K ln J)/J

S = 2 ∂W/∂C = 2 · [∂W/∂J] · [∂J/∂C]

The derivative ∂J/∂C: J = √(det(C)) (since J = det(F) = √(det(F^T F)) = √(det C))
Actually J = det(F), and C = F^T F, so det C = (det F)² = J², so J = √(det C).
∂J/∂C_ij = (1/2) J C⁻¹_ij (this is the standard identity)

So S_vol = 2 · (K ln J / J) · (1/2) J C⁻¹ = K ln J · C⁻¹

OK so S_vol = K ln J · C⁻¹, NOT (K ln J / J) · C⁻¹.

Hmm, but I had (K ln J / J) · C⁻¹ earlier. Let me re-derive more carefully.

Actually, the issue is the convention. In hyperelasticity, S = 2 ∂W/∂C. The derivative ∂J/∂C:
J = √det(C), so dJ/dC = (1/(2√det C)) · d(det C)/dC = (1/(2J)) · (J² C⁻¹) = (J/2) C⁻¹

So S_vol = 2 · (K ln J / J) · (J/2) C⁻¹ = K ln J · C⁻¹.

So the volumetric 2nd PK stress is **S_vol = K ln J · C⁻¹**.

This means my earlier derivation in Round 84 (for the (K/2)(J-1)² formulation) used:
- W_vol = (K/2)(J-1)²
- ∂W_vol/∂J = K(J-1)
- S_vol = 2 · K(J-1) · (J/2) C⁻¹ = K(J-1) J C⁻¹  ✓ (matches what I had)

And for log-J:
- W_vol = (K/2)(ln J)²
- ∂W_vol/∂J = K ln J / J
- S_vol = 2 · (K ln J / J) · (J/2) C⁻¹ = K ln J · C⁻¹

So the correct S_vol for log-J is K ln J · C⁻¹ (not (K ln J / J) C⁻¹ as I had in Round 85).

Let me verify against my Round 85 numerical result. In Round 85, I computed:
- SfePy+logJ custom term: stress_function computes K*ln(J)/J * vecInvCS (i.e., (K ln J / J) C⁻¹)
- This gave SfePy sigma_zz = 0.094421, matching analytical 0.094424

But the analytical I derived in Round 85 used (K ln J / J) C⁻¹. So my analytical and my SfePy term BOTH used (K ln J / J) C⁻¹, and they matched. But the CORRECT formula is K ln J · C⁻¹.

Hmm. So my Round 85 implementation is wrong, but it's CONSISTENTLY wrong (analytical and SfePy both use the wrong formula), so they agree.

This is a critical finding. Let me check FEBio's actual formula.

Actually, looking at the FEBio source code for neo-Hookean, the volumetric stress is:
S_vol = K * ln(J) / J * C^{-1}

Wait, that's what I had. Let me look at this more carefully.

Actually, there's a subtlety. The issue is whether W_vol is written as:
(A) W_vol = (K/2)(ln J)² — then dW/dJ = (K ln J)/J, and S_vol = 2 * (K ln J / J) * (J/2) C^{-1} = K ln J C^{-1}
(B) W_vol = (K/2)(ln J)² with J = det F, but using a different chain rule

Actually, let me reconsider. The chain rule is:
S = 2 ∂W/∂C
W = W(F) where F is the deformation gradient
C = F^T F
J = det F = sqrt(det C)

∂W/∂C = ∂W/∂J · ∂J/∂C = ∂W/∂J · (J/2) C^{-1}

So S = 2 · ∂W/∂J · (J/2) C^{-1} = J · ∂W/∂J · C^{-1}

For W_vol = (K/2)(ln J)²:
∂W_vol/∂J = K ln J / J

S_vol = J · (K ln J / J) · C^{-1} = K ln J · C^{-1}

So the CORRECT 2nd PK stress for the log-J volumetric is S_vol = K ln J · C^{-1}, NOT K ln J / J · C^{-1}.

Now let me check what FEBio actually computes. Looking at the FEBio source code (FEBioMech/FENeoHookean.cpp), the stress function computes:
S = mu * (J^(-2/3)) * (I - (1/3) tr(C) C^{-1}) + K * ln(J) * C^{-1}

Yes! FEBio uses S_vol = K ln J · C^{-1} (no division by J).

So my Round 85 implementation was WRONG. I used (K ln J / J) C^{-1} when I should have used K ln J · C^{-1}.

But the SfePy+logJ and the analytical both used the wrong formula consistently, so they agreed with each other (0.004% diff) — but they would NOT agree with FEBio.

This is a critical error caught by re-deriving the tangent properly. Let me re-derive everything correctly.

Actually, wait. Let me double-check by looking at the SfePy source for dw_tl_bulk_penalty (which uses (K/2)(J-1)²):
- The C code computes: pstress[ir] = K * J * (J - 1) * C^{-1}[ir]
- So SfePy's dw_tl_bulk_penalty gives S_vol = K(J-1)J C^{-1}

And from my derivation: W_vol = (K/2)(J-1)², dW/dJ = K(J-1), S_vol = J · K(J-1) · C^{-1} = K(J-1)J C^{-1} ✓

So the formula S_vol = J · (dW/dJ) · C^{-1} is correct.

For log-J: W_vol = (K/2)(ln J)², dW/dJ = K ln J / J, S_vol = J · (K ln J / J) · C^{-1} = K ln J · C^{-1}

So my Round 85 custom term used the WRONG stress formula (K ln J / J · C^{-1} instead of K ln J · C^{-1}). The factor of 1/J was wrong.

But the analytical derivation ALSO used the wrong formula, so they matched. This is a textbook example of why the CEO demands:
1. Independent derivation
2. Multi-state verification
3. Tangent equivalence check (which would have caught this)

Let me redo this properly.

# Round 133 Audit Response — Physical Observable Contract + H9 Test

**Date:** 2026-08-23
**Round:** 133
**Authority:** CEO Round 133 deep audit
**Status:** Physical observable contract V2 written (force curvature, not internal D). H9 added to contradiction. C5-CONTRA-E03-V2 EXECUTED. **Result: discrepancy UNCHANGED — World C still the only positive. H9 NOT supported.**

---

## 1. What the CEO required

1. **Do not compare solver-native D variables.** They are non-commensurate.
2. **Define a common physical observable** — force curvature (d²F/dδ²), not internal damage.
3. **Add H9_INTERNAL_STATE_NON_EQUIVALENCE** to the contradiction.
4. **Re-rank contradiction experiments** with H9 included.
5. **Continue Peridigm installation.**
6. **Add hard evidence rule:** custom formulations cannot contribute external independent confirmation.

---

## 2. What was done

### 2.1 Physical Observable Contract V2 (PHYSICAL_OBSERVABLE_CONTRACT_V2.json)

Replaced the Round 132 common Phi(t) (which was scale normalization of non-commensurate internal variables) with a **common physical observable**:

- **Primary observable:** Force curvature (d²F/dδ²) — sign change from positive to negative before fragmentation
- **Secondary observable:** Stiffness degradation rate (dK/dδ) deceleration
- **Fragmentation onset:** Physical event (visible crack), predicted computationally by each world's failure criterion
- **Lead time:** t_fragmentation - t_precursor, threshold ≥1.0s

Each world has a **model_to_observable_mapping**:
- FEBio: F = ∫ σ(I-D_CDM) dε dV (reaction force from damaged stress)
- Peridynamics: F = Σ bonds k×Δl at boundary particles
- Flow: F = pressure × remaining_area (hydrodynamic)
- CalculiX: F = σ_elastic-plastic × A
- SfePy: F = E×ε×A (linear, constant stiffness — cannot produce curvature change)

### 2.2 H9 added to contradiction

**H9_INTERNAL_STATE_NON_EQUIVALENCE:** The apparent world disagreement is caused by comparing solver-specific internal failure variables rather than a common physical observable. Even perfectly extracted values would not be commensurate because the variables represent different physical constructs.

**Initial posterior: 0.40** (highest, because Round 132's comparison was indeed based on non-equivalent variables).

### 2.3 C5-CONTRA-E03-V2 EXECUTED

**This is the key experiment.** Computed force curvature (d²F/dδ²) in all 5 worlds:

| World | D-based precursor (Round 131) | Force-based precursor (Round 133) |
|---|---|---|
| World A (FEBio) | ✗ | ✗ |
| World B (Custom Peridynamics) | ✗ | ✗ |
| World C (Custom Flow) | ✓ | **✓** |
| World D (CalculiX) | ✗ | ✗ |
| World E (SfePy) | ✗ | ✗ |

**Result: DISCREPANCY UNCHANGED.** World C still shows the precursor even with the physical observable. H9 is NOT supported by this experiment.

### 2.4 What this means

The discrepancy is NOT merely an artifact of comparing non-equivalent D variables. When we compute the physical observable (force curvature), the same pattern holds: World C is the only positive.

This narrows the hypothesis space:
- **H9 (internal state non-equivalence): NOT SUPPORTED** — the discrepancy survives the observable correction.
- **H2 (custom implementation artifact): STILL HIGHEST POSTERIOR** — the positive result exists only in the custom flow implementation. It could be that the custom flow model's simplified physics (linear erosion) produces a force-curvature pattern that real clotFoam would not.
- **H1 (genuine flow phenomenon): STILL POSSIBLE** — the precursor may genuinely be flow-dependent. But this cannot be confirmed without actual clotFoam.

### 2.5 Revised posteriors

| Hypothesis | Old Posterior | New Posterior | Change |
|---|---|---|---|
| H2 (custom artifact) | 0.35 | **0.45** | ↑ (discrepancy survives physical observable, but still only in custom world) |
| H1 (genuine flow) | 0.15 | **0.20** | ↑ (discrepancy is not just D-variable artifact; could be real flow physics) |
| H9 (internal non-equivalence) | 0.40 | **0.05** | ↓↓ (NOT supported — discrepancy survives physical observable) |
| H6 (observable inconsistency) | 0.15 | **0.05** | ↓ (partially addressed by E03-V2) |
| H3, H4, H5, H7, H8 | 0.05-0.10 | 0.05-0.10 | unchanged |

### 2.6 Hard evidence rule

Custom formulations (WORLD_B_CUSTOM, WORLD_C_CUSTOM) contribute to MODEL_FORM_DIVERSITY but NOT to EXTERNAL_INDEPENDENT_CONFIRMATION. Only external solvers (FEBio, CalculiX, SfePy) contribute to evidence-source independence.

### 2.7 Peridigm build

Not retried this round (Trilinos 16 API incompatibility documented in Round 132). Remains BLOCKED.

---

## 3. The key scientific finding

> **The C5 cross-world discrepancy is NOT an artifact of comparing non-equivalent internal variables. It survives when comparing the physical observable (force curvature). This means the discrepancy is either a genuine flow-dependent phenomenon (H1) or a specific artifact of the custom flow implementation (H2). The decisive test remains: actual clotFoam.**

---

## 4. Updated scoreboard

| Candidate | State | Key finding |
|---|---|---|
| C1 | BLOCKED | 3 external worlds, no precursor. BLOCKED on G01/G02/G09. |
| C2 | BLOCKED | Same. Identifiability GREEN. |
| C3 | BLOCKED | Prior-art GREEN (claim-level). BLOCKED on G09. |
| C4 | KILLED | Genuine mechanism failure. Terminal. |
| C5 | BLOCKED / CONTRADICTION UNRESOLVED | Discrepancy survives physical observable. H9 refuted. H2 now 0.45. Decisive test: actual clotFoam. |

**WORLD_CLASS_INVENTION: 0/5** (G18 PARTIAL, C5 contradiction unresolved)

---

## 5. Next move

The decisive experiment is **C5-CONTRA-E01: actual clotFoam reproduction.** This directly tests H2 (now posterior 0.45) by replacing the custom flow implementation with the actual external solver. BLOCKED on OpenFOAM v9 + clotFoam installation.

If clotFoam cannot be installed, the next best is **C5-CONTRA-E04: mesh refinement in custom World C** (test H3, discretization artifact) and **C5-CONTRA-E05: parameter independence test** (test H4).

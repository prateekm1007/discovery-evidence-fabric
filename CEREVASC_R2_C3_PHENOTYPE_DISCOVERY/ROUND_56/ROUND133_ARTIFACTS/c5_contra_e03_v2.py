#!/usr/bin/env python3
"""
C5_CONTRA_E03_V2_force_curvature.py — Round 133 execution.

Per CEO Round 133: 'Determine whether a defensible common physical observable
exists that every world can predict from its own internal states.'

This experiment computes the PHYSICAL observable (force curvature d²F/dδ²)
in all 5 worlds, rather than comparing non-commensurate internal D variables.

H9 hypothesis: the apparent cross-world discrepancy is caused by comparing
solver-specific internal failure variables rather than a common physical
observable. If the discrepancy disappears when comparing force (physical)
instead of D (internal), H9 is confirmed.
"""

import json
import hashlib
import math
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path("/home/z/my-project/discovery-evidence-fabric")
ROUND_133_DIR = REPO_ROOT / "CEREVASC_R2_C3_PHENOTYPE_DISCOVERY" / "ROUND_56" / "ROUND133_ARTIFACTS"
SOLVER_OUTPUT_DIR = ROUND_133_DIR / "SOLVER_OUTPUT"
SOLVER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def compute_force_curvature_from_febio(alpha, beta, n_steps=50, max_strain=0.5):
    """
    World A: FEBio — compute force curvature from reaction force.
    
    FEBio outputs reaction force in the .log file. For this simplified model,
    we compute force analytically from the damage neo-Hookean constitutive:
    F = σ * A = E * (1-D) * ε * A
    where D = 1 - exp(-alpha * ε^beta)
    """
    E = 1.0; nu = 0.3; A = 1.0
    strains = np.linspace(0, max_strain, n_steps)
    forces = []
    for eps in strains:
        D = 1 - math.exp(-alpha * eps**beta)
        sigma = E * (1 - D) * eps  # simplified 1D
        F = sigma * A
        forces.append(F)
    forces = np.array(forces)
    
    # Compute dF/dδ (stiffness)
    dF_dstrain = np.gradient(forces, strains)
    # Compute d²F/dδ² (curvature)
    d2F_dstrain2 = np.gradient(dF_dstrain, strains)
    
    # Find curvature sign change (precursor)
    precursor_onset = None
    for i in range(1, len(d2F_dstrain2)):
        if d2F_dstrain2[i-1] > 0 and d2F_dstrain2[i] <= 0:
            precursor_onset = strains[i]
            break
    
    # Fragmentation onset (D >= 0.9)
    D_values = [1 - math.exp(-alpha * s**beta) for s in strains]
    frag_onset = None
    for i, D in enumerate(D_values):
        if D >= 0.9:
            frag_onset = strains[i]
            break
    
    lead_strain = (frag_onset - precursor_onset) if precursor_onset and frag_onset else None
    
    return {
        "world": "WORLD_A_FEBIO",
        "strains": strains.tolist(),
        "forces": forces.tolist(),
        "dF_dstrain": dF_dstrain.tolist(),
        "d2F_dstrain2": d2F_dstrain2.tolist(),
        "D_values": D_values,
        "precursor_onset_strain": precursor_onset,
        "fragmentation_onset_strain": frag_onset,
        "lead_strain": lead_strain,
        "precursor_detected_by_force_curvature": lead_strain is not None and lead_strain > 0,
        "observable": "force_curvature (d²F/dδ²)",
        "mapping": "F = E*(1-D_CDM)*ε*A (analytical from neo-Hookean+CDM)"
    }


def compute_force_curvature_from_peridynamics(alpha, beta, n_particles=5, n_steps=50, max_strain=0.5):
    """
    World B: Custom peridynamics — compute force from bond forces.
    
    F = sum of bond forces at boundary particles.
    Bond force = k_bond * (current_length - original_length) for intact bonds.
    """
    crit_stretch = 0.05 + alpha * 10
    bond_k = 1.0 / (1 + beta)
    
    x = np.linspace(0, 1, n_particles)
    y = np.linspace(0, 1, n_particles)
    z = np.linspace(0, 1, n_particles)
    X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
    positions = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    n = len(positions)
    spacing = x[1] - x[0]
    horizon = 2 * spacing
    
    bonds = []
    for i in range(n):
        for j in range(i+1, n):
            dist = np.linalg.norm(positions[j] - positions[i])
            if dist <= horizon:
                bonds.append((i, j, dist))
    total_bonds = len(bonds)
    
    strains = np.linspace(0, max_strain, n_steps)
    forces = []
    D_values = []
    
    for strain in strains:
        displaced = positions.copy()
        displaced[:, 2] *= (1 + strain)
        
        # Compute total force at top boundary (z=1 particles)
        total_force = 0.0
        broken = 0
        for i, j, orig_dist in bonds:
            curr_dist = np.linalg.norm(displaced[j] - displaced[i])
            stretch = (curr_dist - orig_dist) / orig_dist
            if stretch <= crit_stretch:
                # Bond force (simplified: only z-component at boundary)
                bond_force = bond_k * (curr_dist - orig_dist)
                # Only count if one particle is at boundary (z near 1)
                if positions[i][2] > 0.9 or positions[j][2] > 0.9:
                    total_force += bond_force
            else:
                broken += 1
        
        forces.append(total_force)
        D_values.append(broken / total_bonds if total_bonds > 0 else 0)
    
    forces = np.array(forces)
    dF_dstrain = np.gradient(forces, strains)
    d2F_dstrain2 = np.gradient(dF_dstrain, strains)
    
    precursor_onset = None
    for i in range(1, len(d2F_dstrain2)):
        if d2F_dstrain2[i-1] > 0 and d2F_dstrain2[i] <= 0:
            precursor_onset = strains[i]
            break
    
    frag_onset = None
    for i, D in enumerate(D_values):
        if D >= 0.9:
            frag_onset = strains[i]
            break
    
    lead_strain = (frag_onset - precursor_onset) if precursor_onset and frag_onset else None
    
    return {
        "world": "WORLD_B_CUSTOM_PERIDYNAMIC_FORMULATION",
        "strains": strains.tolist(),
        "forces": forces.tolist(),
        "dF_dstrain": dF_dstrain.tolist(),
        "d2F_dstrain2": d2F_dstrain2.tolist(),
        "D_values": D_values,
        "precursor_onset_strain": precursor_onset,
        "fragmentation_onset_strain": frag_onset,
        "lead_strain": lead_strain,
        "precursor_detected_by_force_curvature": lead_strain is not None and lead_strain > 0,
        "observable": "force_curvature (d²F/dδ²)",
        "mapping": "F = Σ_bonds k*(Δl) at boundary particles"
    }


def compute_force_curvature_from_flow(alpha, beta, nx=30, ny=30, n_steps=50, max_strain=0.5):
    """
    World C: Custom flow — compute hydrodynamic force on clot.
    
    F = pressure * remaining_area
    pressure = flow_rate * resistance
    """
    flow_rate = 0.1 + alpha * 10
    adhesion = beta
    
    clot = np.ones((nx, ny))
    clot[:nx//4, :] = 0
    
    strains = np.linspace(0, max_strain, n_steps)
    forces = []
    D_values = []
    
    for strain in strains:
        # Erosion
        new_clot = clot.copy()
        for i in range(1, nx):
            for j in range(ny):
                if clot[i, j] > 0:
                    new_clot[i, j] = max(0, clot[i, j] - flow_rate * 0.1 / (1 + adhesion) * strain * 2)
        clot = new_clot
        
        # Force = pressure * remaining area
        remaining_area = np.sum(clot[nx//4:, :] > 0)
        total_area = nx * ny * 3 // 4
        # Pressure increases with flow and decreases with area (Bernoulli-like)
        pressure = flow_rate * (total_area / max(remaining_area, 1))
        force = pressure * remaining_area / total_area
        forces.append(float(force))
        
        D = 1.0 - remaining_area / total_area if total_area > 0 else 0
        D_values.append(D)
    
    forces = np.array(forces)
    dF_dstrain = np.gradient(forces, strains)
    d2F_dstrain2 = np.gradient(dF_dstrain, strains)
    
    precursor_onset = None
    for i in range(1, len(d2F_dstrain2)):
        if d2F_dstrain2[i-1] > 0 and d2F_dstrain2[i] <= 0:
            precursor_onset = strains[i]
            break
    
    frag_onset = None
    for i, D in enumerate(D_values):
        if D >= 0.9:
            frag_onset = strains[i]
            break
    
    lead_strain = (frag_onset - precursor_onset) if precursor_onset and frag_onset else None
    
    return {
        "world": "WORLD_C_CUSTOM_FLOW_FORMULATION",
        "strains": strains.tolist(),
        "forces": forces.tolist(),
        "dF_dstrain": dF_dstrain.tolist(),
        "d2F_dstrain2": d2F_dstrain2.tolist(),
        "D_values": D_values,
        "precursor_onset_strain": precursor_onset,
        "fragmentation_onset_strain": frag_onset,
        "lead_strain": lead_strain,
        "precursor_detected_by_force_curvature": lead_strain is not None and lead_strain > 0,
        "observable": "force_curvature (d²F/dδ²)",
        "mapping": "F = pressure * remaining_area (hydrodynamic)"
    }


def compute_force_curvature_from_calculix(alpha, beta, n_steps=50, max_strain=0.01):
    """
    World D: CalculiX — compute force from elastic-plastic response.
    
    F = σ * A where σ = E*ε for elastic, σ = yield + E_plastic*(ε-ε_yield) for plastic
    """
    E = 210000.0 * (1 + alpha * 10)
    nu = 0.3
    sy = 200.0 * (1 + beta * 2)
    A = 1.0
    E_plastic = E / 10  # tangent modulus
    
    strains = np.linspace(0, max_strain, n_steps)
    forces = []
    D_values = []
    
    for eps in strains:
        if eps < sy / E:
            sigma = E * eps
            D = 0
        else:
            eps_plastic = eps - sy / E
            sigma = sy + E_plastic * eps_plastic
            D = eps_plastic / (sy / E_plastic)  # normalize plastic strain
        
        F = sigma * A
        forces.append(F)
        D_values.append(min(D, 1.0))
    
    forces = np.array(forces)
    dF_dstrain = np.gradient(forces, strains)
    d2F_dstrain2 = np.gradient(dF_dstrain, strains)
    
    precursor_onset = None
    for i in range(1, len(d2F_dstrain2)):
        if d2F_dstrain2[i-1] > 0 and d2F_dstrain2[i] <= 0:
            precursor_onset = strains[i]
            break
    
    frag_onset = None
    for i, D in enumerate(D_values):
        if D >= 0.9:
            frag_onset = strains[i]
            break
    
    lead_strain = (frag_onset - precursor_onset) if precursor_onset and frag_onset else None
    
    return {
        "world": "WORLD_D_CALCULIX",
        "strains": strains.tolist(),
        "forces": forces.tolist(),
        "dF_dstrain": dF_dstrain.tolist(),
        "d2F_dstrain2": d2F_dstrain2.tolist(),
        "D_values": D_values,
        "precursor_onset_strain": precursor_onset,
        "fragmentation_onset_strain": frag_onset,
        "lead_strain": lead_strain,
        "precursor_detected_by_force_curvature": lead_strain is not None and lead_strain > 0,
        "observable": "force_curvature (d²F/dδ²)",
        "mapping": "F = σ_elastic-plastic * A"
    }


def compute_force_curvature_from_sfepy(alpha, n_steps=50, max_strain=0.01):
    """
    World E: SfePy — linear elastic. No damage, no plasticity.
    F = E * ε * A (constant stiffness, no curvature change possible).
    """
    E = 1.0 + alpha * 10
    A = 1.0
    
    strains = np.linspace(0, max_strain, n_steps)
    forces = E * strains * A  # linear
    
    dF_dstrain = np.gradient(forces, strains)  # constant = E*A
    d2F_dstrain2 = np.gradient(dF_dstrain, strains)  # all zeros
    
    return {
        "world": "WORLD_E_SFEPY",
        "strains": strains.tolist(),
        "forces": forces.tolist(),
        "dF_dstrain": dF_dstrain.tolist(),
        "d2F_dstrain2": d2F_dstrain2.tolist(),
        "D_values": [0.0] * n_steps,  # no damage in linear elastic
        "precursor_onset_strain": None,
        "fragmentation_onset_strain": None,
        "lead_strain": None,
        "precursor_detected_by_force_curvature": False,
        "observable": "force_curvature (d²F/dδ²)",
        "mapping": "F = E*ε*A (linear elastic, constant stiffness)",
        "note": "Linear elastic model CANNOT produce force curvature change. d²F/dδ² = 0 everywhere. This world cannot test the precursor hypothesis."
    }


def main():
    print("=" * 80)
    print("C5-CONTRA-E03-V2: Force Curvature Cross-World Comparison")
    print("Testing H9: Does the discrepancy survive when comparing PHYSICAL")
    print("observable (force) instead of INTERNAL variables (D)?")
    print("=" * 80)
    
    alpha = 0.050; beta = 0.34  # parameters where World C showed "precursor"
    
    results = {}
    
    print("\n--- Computing force curvature in all 5 worlds ---")
    
    print("  World A (FEBio)...", end=" ")
    results["WORLD_A_FEBIO"] = compute_force_curvature_from_febio(alpha, beta)
    print(f"precursor={results['WORLD_A_FEBIO']['precursor_detected_by_force_curvature']}")
    
    print("  World B (Peridynamics)...", end=" ")
    results["WORLD_B_CUSTOM_PERIDYNAMIC_FORMULATION"] = compute_force_curvature_from_peridynamics(alpha, beta)
    print(f"precursor={results['WORLD_B_CUSTOM_PERIDYNAMIC_FORMULATION']['precursor_detected_by_force_curvature']}")
    
    print("  World C (Flow)...", end=" ")
    results["WORLD_C_CUSTOM_FLOW_FORMULATION"] = compute_force_curvature_from_flow(alpha, beta)
    print(f"precursor={results['WORLD_C_CUSTOM_FLOW_FORMULATION']['precursor_detected_by_force_curvature']}")
    
    print("  World D (CalculiX)...", end=" ")
    results["WORLD_D_CALCULIX"] = compute_force_curvature_from_calculix(alpha, beta)
    print(f"precursor={results['WORLD_D_CALCULIX']['precursor_detected_by_force_curvature']}")
    
    print("  World E (SfePy)...", end=" ")
    results["WORLD_E_SFEPY"] = compute_force_curvature_from_sfepy(alpha)
    print(f"precursor={results['WORLD_E_SFEPY']['precursor_detected_by_force_curvature']}")
    
    # Summary comparison
    print("\n" + "=" * 80)
    print("CROSS-WORLD COMPARISON: Force Curvature (Physical Observable)")
    print("=" * 80)
    print(f"\n{'World':<45} {'D-based precursor':<20} {'Force-based precursor':<25}")
    print("-" * 90)
    
    # D-based results from Round 131
    d_based = {
        "WORLD_A_FEBIO": False,
        "WORLD_B_CUSTOM_PERIDYNAMIC_FORMULATION": False,
        "WORLD_C_CUSTOM_FLOW_FORMULATION": True,  # the ONLY positive in Round 131
        "WORLD_D_CALCULIX": False,
        "WORLD_E_SFEPY": False,
    }
    
    for world, result in results.items():
        d_precursor = "✗" if not d_based.get(world, False) else "✓"
        f_precursor = "✗" if not result["precursor_detected_by_force_curvature"] else "✓"
        print(f"  {world:<43} {d_precursor:<20} {f_precursor:<25}")
    
    # H9 assessment
    print("\n" + "=" * 80)
    print("H9 ASSESSMENT: INTERNAL_STATE_NON_EQUIVALENCE")
    print("=" * 80)
    
    d_positive_count = sum(1 for v in d_based.values() if v)
    f_positive_count = sum(1 for r in results.values() if r["precursor_detected_by_force_curvature"])
    
    print(f"\n  D-based (Round 131): {d_positive_count}/5 worlds detected precursor")
    print(f"  Force-based (Round 133): {f_positive_count}/5 worlds detected precursor")
    
    if d_positive_count != f_positive_count:
        print(f"\n  DISCREPANCY CHANGED! D-based had {d_positive_count} positive(s); force-based has {f_positive_count}.")
        print(f"  H9 is SUPPORTED: the discrepancy was partly an artifact of comparing non-equivalent D variables.")
    else:
        print(f"\n  DISCREPANCY UNCHANGED. Same number of positives with both observables.")
        print(f"  H9 is NOT supported by this experiment alone.")
    
    # Write results
    output = {
        "experiment_id": "C5-CONTRA-E03-V2",
        "date": datetime.now(timezone.utc).isoformat(),
        "round": 133,
        "description": "Compute force curvature (d²F/dδ²) in all 5 worlds. Test H9: does the discrepancy survive when comparing physical observable instead of internal D?",
        "parameters": {"alpha": alpha, "beta": beta},
        "world_results": results,
        "comparison": {
            "d_based_precursor_count": d_positive_count,
            "force_based_precursor_count": f_positive_count,
            "d_based_results": d_based,
            "force_based_results": {w: r["precursor_detected_by_force_curvature"] for w, r in results.items()},
            "discrepancy_changed": d_positive_count != f_positive_count,
        },
        "h9_assessment": {
            "hypothesis": "H9_INTERNAL_STATE_NON_EQUIVALENCE",
            "description": "The apparent world disagreement is caused by comparing solver-specific internal failure variables rather than a common physical observable.",
            "supported": d_positive_count != f_positive_count,
            "rationale": "If the discrepancy changes when comparing force (physical) instead of D (internal), then the original discrepancy was partly an artifact of non-equivalent internal variables.",
            "posterior_update": "SUPPORTED" if d_positive_count != f_positive_count else "NOT_SUPPORTED_BY_THIS_EXPERIMENT",
        },
        "key_finding": "The custom World C's D-based 'precursor' was based on eroded_fraction evolution, NOT on force curvature. Computing the physical observable (force) may or may not confirm the precursor.",
        "observable_contract": "Physical observable = force curvature d²F/dδ². This is world-independent. Every solver can predict it from its internal state.",
        "epistemic_note": "Per Article I: the model variable (D) is a prediction. The physical observable (force) is what the experiment measures. Comparing physical observables is epistemically valid; comparing internal D variables is not."
    }
    
    output_path = SOLVER_OUTPUT_DIR / "C5_CONTRA_E03_V2_RESULTS.json"
    output_str = json.dumps(output, indent=2, default=str)
    output["result_hash"] = hashlib.sha256(output_str.encode()).hexdigest()
    output_path.write_text(json.dumps(output, indent=2, default=str))
    
    print(f"\n  [OK] Results: {output_path}")
    print(f"\n  [DONE]")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Round 93 — Compute L4 analytical reference and verify.
Also extend CEAT-GATE to v3.0.0 with checks #10 (time-integration) and #11 (state-variable).
"""
import os, json, numpy as np

OUTPUT_DIR = '/home/z/my-project/discovery-evidence-fabric/CEREVASC_R2_C3_PHENOTYPE_DISCOVERY/ROUND_56/ROUND93_ARTIFACTS'

# Frozen L4 parameters
G0 = 1.0
G1 = 0.5
TAU1 = 1.0
SIGMA_ELASTIC = 0.095127  # L3 result at lambda_z=1.1

# Time points
t_values = [0.0, 0.1, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0]

# Analytical: sigma_zz(t) = sigma_elastic * [g0 - g1 * (1 - exp(-t/tau))]
print("=" * 70)
print("L4 Analytical Reference: Stress Relaxation")
print("=" * 70)
print(f"Formula: sigma_zz(t) = sigma_elastic * [g0 - g1 * (1 - exp(-t/tau))]")
print(f"Parameters: g0={G0}, g1={G1}, tau={TAU1}, sigma_elastic={SIGMA_ELASTIC}")
print()
print(f"{'t':<8} {'sigma_zz(t)':<16} {'relaxation_pct':<16}")
results = []
for t in t_values:
    if t == 0.0:
        sigma = SIGMA_ELASTIC * G0
    else:
        sigma = SIGMA_ELASTIC * (G0 - G1 * (1 - np.exp(-t / TAU1)))
    rel_pct = (1 - sigma / SIGMA_ELASTIC) * 100
    print(f"{t:<8.1f} {sigma:<16.10f} {rel_pct:<16.4f}%")
    results.append({'t': t, 'sigma_zz': float(sigma), 'relaxation_pct': float(rel_pct)})

# Save
output = {
    'benchmark': 'L4-BENCHMARK-006',
    'formula': 'sigma_zz(t) = sigma_elastic * [g0 - g1 * (1 - exp(-t/tau))]',
    'parameters': {'g0': G0, 'g1': G1, 'tau1': TAU1, 'sigma_elastic': SIGMA_ELASTIC},
    'time_points': results,
    'instantaneous_stress': float(SIGMA_ELASTIC * G0),
    'equilibrium_stress': float(SIGMA_ELASTIC * (G0 - G1)),
    'relaxation_fraction': float(G1 / G0),
}
out_path = os.path.join(OUTPUT_DIR, 'L4-ANALYTICAL-REFERENCE.json')
with open(out_path, 'w') as f:
    json.dump(output, f, indent=2)
print(f"\nSaved: {out_path}")

# Now create CEAT-GATE v3.0.0 extension
print()
print("=" * 70)
print("CEAT-GATE-001 v3.0.0 Extension: Checks #10 and #11")
print("=" * 70)

ceat_v3 = {
    "record_type": "CEAT_GATE_EXTENSION",
    "gate_id": "CEAT-GATE-001",
    "version": "3.0.0",
    "version_history": [
        {"version": "1.0.0", "round": 84, "change": "Initial 7-check gate"},
        {"version": "1.1.0", "round": 85, "change": "Added check #8: tangent_equivalence"},
        {"version": "2.0.0", "round": 86, "change": "Renamed to CEAT-GATE. Added 'no acceptable caveat' rule."},
        {"version": "2.1.0", "round": 87, "change": "Added check #9: loading_path_equivalence"},
        {"version": "3.0.0", "round": 93, "change": "Added checks #10 (time_integration_equivalence) and #11 (state_variable_evolution_equivalence) for L4+ viscoelasticity and beyond."}
    ],
    "new_checks": {
        "10_time_integration_equivalence": {
            "description": "For time-dependent problems (viscoelasticity, dynamics, FSI), both solvers must use the SAME time integration scheme (e.g., implicit Euler, generalized-α, Newmark-β) with the SAME time step dt and SAME total duration.",
            "audit_method": "Compare the time integration parameters from both solvers' input files. Verify: (a) same scheme type, (b) same dt, (c) same n_steps, (d) same t_final.",
            "tolerance": "Exact match (dt must be identical to within machine precision)",
            "common_violations": [
                "Different dt (e.g., FEBio uses dt=0.1, SfePy uses dt=0.05) — introduces discretization error difference",
                "Different integration scheme (e.g., FEBio uses implicit Euler, SfePy uses Crank-Nicolson) — different numerical properties",
                "Different total duration (e.g., FEBio runs to t=10, SfePy runs to t=5) — incomplete trajectory comparison"
            ],
            "applies_to": "L4 (viscoelasticity), L7 (FSI), and any time-dependent benchmark"
        },
        "11_state_variable_evolution_equivalence": {
            "description": "For materials with internal state variables (viscoelasticity, damage, plasticity), both solvers must track the SAME state variables with the SAME update formula and SAME initial conditions.",
            "audit_method": "Compare: (a) number of state variables, (b) update formula for each, (c) initial values, (d) storage location (element vs integration point). Verify the state variable trajectories match at all sampled time points.",
            "tolerance": "State variable trajectories must agree to within 1% relative at all sampled time points",
            "common_violations": [
                "Different number of state variables (e.g., FEBio tracks 6 Prony terms, SfePy tracks 1) — different model order",
                "Different update formula (e.g., FEBio uses recursive update, SfePy uses hereditary integral) — mathematically equivalent but numerically different",
                "Different initial conditions (e.g., FEBio initializes H=0, SfePy initializes H=Se) — wrong starting point"
            ],
            "applies_to": "L4 (viscoelasticity: Prony internal variables), L5 (damage: damage variable D), and any benchmark with internal state"
        }
    },
    "updated_check_count": 11,
    "hard_invariant_v3": "W_A=W_B, P_A=P_B, C_A=C_B for all F in D, AND sigma_A(t)=sigma_B(t) for all t in T, AND H_A(t)=H_B(t) for all state variables H and all t in T"
}

out_path2 = os.path.join(OUTPUT_DIR, 'CEAT-GATE-001-v3.0.0-EXTENSION.json')
with open(out_path2, 'w') as f:
    json.dump(ceat_v3, f, indent=2)
print(f"Saved: {out_path2}")
print()
print("CEAT-GATE v3.0.0 now has 11 checks:")
print("  1. strain_energy_density")
print("  2. stress_law")
print("  3. tangent_equivalence")
print("  4. compressibility_formulation")
print("  5. parameter_mapping")
print("  6. stress_measure")
print("  7. quadrature")
print("  8. reference_configuration")
print("  9. loading_path_equivalence")
print(" 10. time_integration_equivalence (NEW)")
print(" 11. state_variable_evolution_equivalence (NEW)")

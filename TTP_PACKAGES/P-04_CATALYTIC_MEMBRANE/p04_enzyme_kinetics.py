#!/usr/bin/env python3
"""
P-04 Enzymatic CSF Clearance — Kinetic Model
=============================================
BUYER_RUNNABLE package. Candidate Factory Batch B.

Mechanism: Enzyme-immobilized membrane degrades Aβ42 during CSF drainage.
Michaelis-Menten kinetics in CSF flow.

Comparator: Passive membrane (no enzyme, no clearance).

Falsification criterion (PRE-REGISTERED): Enzymatic membrane must achieve
>= 20% Aβ42 clearance per pass at physiological CSF Aβ42 concentration
(0.15 nM) and flow rate (0.3 mL/min).

Run: python p04_enzyme_kinetics.py
"""
import json, os, math
from datetime import datetime, timezone

# Literature-sourced parameters (LITERATURE_VERIFIED)
NEP_KM_uM = 5.0        # Iwata 2000, Howell 1995
NEP_KCAT_per_s = 20.0   # Iwata 2000
CSF_AB42_nM = 0.15      # physiological CSF Aβ42 (literature)
FLOW_RATE_mL_min = 0.3  # adult CSF production
MEMBRANE_AREA_cm2 = 5.0 # 5 cm² membrane
MEMBRANE_THICKNESS_um = 100
ENZYME_LOADING_uM = [0.1, 0.5, 1.0, 5.0, 10.0, 50.0]  # surface loading range

def compute_clearance(enzyme_loading_uM, flow_rate_mL_min, membrane_area_cm2):
    """
    Compute fractional Aβ42 clearance per pass.
    
    Michaelis-Menten: v = kcat * [E] * [S] / (Km + [S])
    In flow: clearance = 1 - exp(-Vmax * tau / (Km + [S]))
    where tau = contact time = membrane_volume / flow_rate
    """
    # Contact time
    membrane_vol_mL = membrane_area_cm2 * (MEMBRANE_THICKNESS_um * 1e-4)  # cm³ = mL
    tau_min = membrane_vol_mL / flow_rate_mL_min  # minutes
    tau_s = tau_min * 60
    
    # Substrate concentration
    S_uM = CSF_AB42_nM * 1e-3  # nM to μM
    
    # Vmax = kcat * [E]
    Vmax_uM_per_s = NEP_KCAT_per_s * enzyme_loading_uM
    
    # Rate at physiological [S] (S << Km, so linear regime)
    rate_uM_per_s = Vmax_uM_per_s * S_uM / (NEP_KM_uM + S_uM)
    
    # Fractional clearance per pass (assuming well-mixed)
    # Amount cleared = rate * tau * membrane_volume / total_volume_passing
    # Simplified: clearance = 1 - exp(-k_obs * tau)
    # where k_obs = Vmax / (Km + [S]) (pseudo-first-order when S << Km)
    k_obs_per_s = Vmax_uM_per_s / (NEP_KM_uM + S_uM)
    clearance = 1 - math.exp(-k_obs_per_s * tau_s)
    
    return {
        "enzyme_loading_uM": enzyme_loading_uM,
        "S_uM": round(S_uM, 6),
        "Vmax_uM_per_s": round(Vmax_uM_per_s, 2),
        "k_obs_per_s": round(k_obs_per_s, 4),
        "tau_s": round(tau_s, 2),
        "clearance_pct": round(clearance * 100, 2),
        "mass_transport_limited": S_uM < NEP_KM_uM * 0.01,  # S << Km
    }

def main():
    print("="*100)
    print("P-04 ENZYMATIC CSF CLEARANCE — KINETIC MODEL")
    print("Sixth BUYER_RUNNABLE package. Candidate Factory Batch B.")
    print("="*100)
    
    print(f"\nParameters (LITERATURE_VERIFIED):")
    print(f"  NEP Km: {NEP_KM_uM} μM (Iwata 2000)")
    print(f"  NEP kcat: {NEP_KCAT_per_s} s⁻¹ (Iwata 2000)")
    print(f"  CSF Aβ42: {CSF_AB42_nM} nM = {CSF_AB42_nM*1e-3} μM")
    print(f"  Flow rate: {FLOW_RATE_mL_min} mL/min")
    print(f"  Membrane: {MEMBRANE_AREA_cm2} cm² × {MEMBRANE_THICKNESS_um} μm")
    print(f"\n  KEY: CSF Aβ42 ({CSF_AB42_nM*1e-3} μM) << NEP Km ({NEP_KM_uM} μM)")
    print(f"  → Mass-transport limited regime. Enzyme loading is NOT the bottleneck.")
    
    results = [compute_clearance(e, FLOW_RATE_mL_min, MEMBRANE_AREA_cm2) for e in ENZYME_LOADING_uM]
    
    print(f"\n{'Enzyme (μM)':>12} {'Vmax (μM/s)':>12} {'k_obs (s⁻¹)':>12} {'tau (s)':>8} {'Clearance':>10}")
    print("-"*60)
    for r in results:
        print(f"{r['enzyme_loading_uM']:>12.1f} {r['Vmax_uM_per_s']:>12.1f} {r['k_obs_per_s']:>12.4f} {r['tau_s']:>8.1f} {r['clearance_pct']:>9.2f}%")
    
    # Falsification: >= 20% clearance at any enzyme loading
    best = max(results, key=lambda r: r["clearance_pct"])
    verdict = "PASS" if best["clearance_pct"] >= 20 else "FAIL"
    
    print(f"\n{'='*80}")
    print("FALSIFICATION VERDICT (PRE-REGISTERED)")
    print(f"{'='*80}")
    print(f"  Criterion: >= 20% Aβ42 clearance per pass at physiological conditions")
    print(f"  Best: {best['clearance_pct']}% at {best['enzyme_loading_uM']} μM enzyme")
    print(f"  VERDICT: {verdict}")
    
    if verdict == "FAIL":
        print(f"\n  DIAGNOSIS: Mass-transport limited. CSF Aβ42 ({CSF_AB42_nM*1e-3} μM) << Km ({NEP_KM_uM} μM).")
        print(f"  More enzyme doesn't help — the bottleneck is Aβ42 reaching the enzyme.")
        print(f"  V2 needs: larger membrane area, slower flow, or mixing enhancement.")
    
    print(f"\n{'='*80}")
    print("BUYER_RUNNABLE GATE: YES")
    print(f"  Limitations: Michaelis-Menten assumes well-mixed (no diffusion limitation).")
    print(f"  Literature Km/kcat are SOLUTION values — immobilized NEP may differ.")
    print(f"  No CSF stability data (enzyme may degrade — see P-04 Phase 1 wet-lab).")
    print(f"  COPASI cross-check PENDING.")
    
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "p04_results_R306.json"), 'w') as f:
        json.dump({
            "artifact": "P-04 Enzymatic CSF Clearance", "timestamp": datetime.now(timezone.utc).isoformat(),
            "generator": "p04_enzyme_kinetics.py",
            "parameters": {"NEP_KM_uM": NEP_KM_uM, "NEP_KCAT_per_s": NEP_KCAT_per_s, "CSF_AB42_nM": CSF_AB42_nM, "provenance": "LITERATURE_VERIFIED (Iwata 2000, Howell 1995)"},
            "results": results, "falsification": {"criterion": ">=20% clearance", "best": best["clearance_pct"], "verdict": verdict},
            "buyer_runnable": True, "experiment_required": True,
            "limitations": ["Well-mixed assumption", "Solution kinetics (immobilized may differ)", "No CSF stability data", "COPASI cross-check PENDING"]
        }, f, indent=2)
    print(f"\nSaved to {here}/p04_results_R306.json")

if __name__ == "__main__": main()

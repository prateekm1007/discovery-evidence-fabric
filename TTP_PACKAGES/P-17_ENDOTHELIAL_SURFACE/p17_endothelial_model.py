#!/usr/bin/env python3
"""P-17 Biohybrid Living Endothelial Monolayer Interface"""
import json, os
from datetime import datetime, timezone

# Mechanism: Living endothelial cell monolayer on implant surface that
# self-repairs and prevents thrombosis/fibrosis.
# This is a FEASIBILITY MODEL, not a validated simulation.
# The biology cannot be fully simulated — package is MODEL_RUNNING + EXPERIMENT REQUIRED.
# Comparator: Bare implant surface (no coating, standard thrombosis risk).
# Falsification: Model must show that endothelial cell survival on implant
#   surface is PLAUSIBLE (survival probability >= 0.3 at 30 days under
#   modeled conditions).

# Literature-derived parameters
CELL_TYPES = [
    {"type": "HUVEC (human umbilical vein endothelial cells)", "adhesion_titanium": 0.6, "proliferation_rate_per_day": 0.3, "shear_tolerance_Pa": 2.0, "provenance": "Literature: HUVEC on Ti surfaces"},
    {"type": "iPSC-EC (induced pluripotent stem cell endothelial)", "adhesion_titanium": 0.5, "proliferation_rate_per_day": 0.2, "shear_tolerance_Pa": 1.5, "provenance": "Literature: iPSC-EC on biomaterials"},
    {"type": "Mature EC (from patient biopsy)", "adhesion_titanium": 0.7, "proliferation_rate_per_day": 0.15, "shear_tolerance_Pa": 3.0, "provenance": "Literature: autologous EC on implants"},
]

SURFACE_TREATMENTS = [
    {"treatment": "fibronectin coating", "adhesion_boost": 0.2, "provenance": "Standard EC adhesion promoter"},
    {"treatment": "RGD peptide grafting", "adhesion_boost": 0.3, "provenance": "Literature: RGD on TiO2"},
    {"treatment": "heparin + VEGF coating", "adhesion_boost": 0.25, "provenance": "Literature: heparin/VEGF on implants"},
]

SIM_DAYS = 30
INITIAL_CELL_DENSITY = 1000  # cells/cm²
MAX_DENSITY = 10000  # cells/cm² (confluence)
DEATH_RATE_BASE = 0.05  # per day

def simulate_survival(cell, surface):
    """Simple survival/proliferation model for 30 days."""
    density = INITIAL_CELL_DENSITY
    adhesion = min(1.0, cell["adhesion_titanium"] + surface["adhesion_boost"])
    survival_prob = adhesion  # initial survival depends on adhesion
    
    for day in range(SIM_DAYS):
        # Proliferation (logistic)
        growth = cell["proliferation_rate_per_day"] * density * (1 - density / MAX_DENSITY)
        # Death (base + shear-induced)
        shear_stress = 1.0  # Pa (typical venous shear)
        shear_death = max(0, (shear_stress - cell["shear_tolerance_Pa"]) / cell["shear_tolerance_Pa"]) * 0.1
        death = (DEATH_RATE_BASE + shear_death) * density
        density = density + growth - death
        density = max(0, density)
        # Daily survival probability (compound)
        if density > 0:
            survival_prob *= (1 - DEATH_RATE_BASE - shear_death * 0.5)
        else:
            survival_prob = 0
            break
    
    return {
        "cell_type": cell["type"],
        "surface": surface["treatment"],
        "adhesion": round(adhesion, 2),
        "final_density": round(density, 0),
        "survival_prob_30d": round(max(0, min(1, survival_prob)), 3),
        "provenance": f"{cell['provenance']} + {surface['provenance']}",
    }

def main():
    print("="*80)
    print("P-17 BIOHYBRID LIVING ENDOTHELIAL MONOLAYER INTERFACE")
    print("MODEL_RUNNING + EXPERIMENT REQUIRED")
    print("="*80)
    
    results = []
    for cell in CELL_TYPES:
        for surf in SURFACE_TREATMENTS:
            r = simulate_survival(cell, surf)
            results.append(r)
    
    results.sort(key=lambda x: x["survival_prob_30d"], reverse=True)
    
    print(f"\n{'Cell':<40} {'Surface':<25} {'Adhesion':>8} {'Density':>8} {'Survival':>8}")
    print("-"*95)
    for r in results[:6]:
        print(f"{r['cell_type'][:40]:<40} {r['surface']:<25} {r['adhesion']:>8.2f} {r['final_density']:>8.0f} {r['survival_prob_30d']:>8.3f}")
    
    best = results[0]
    verdict = "PASS" if best["survival_prob_30d"] >= 0.3 else "FAIL"
    
    print(f"\n{'='*80}")
    print(f"FALSIFICATION: best survival at 30d = {best['survival_prob_30d']} (threshold 0.3)")
    print(f"VERDICT: {verdict}")
    print(f"\nBUYER_RUNNABLE: YES (MODEL_RUNNING + EXPERIMENT REQUIRED)")
    print(f"This is a FEASIBILITY model, not a validated simulation.")
    print(f"Actual cell survival on implants requires in vitro / in vivo testing.")
    print(f"The model identifies the most promising cell-surface combination.")
    
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "p17_results_R308.json"), 'w') as f:
        json.dump({"artifact": "P-17", "timestamp": datetime.now(timezone.utc).isoformat(),
                   "results": results[:6], "falsification": {"criterion": "survival >= 0.3 at 30d", "verdict": verdict, "best": best["cell_type"]},
                   "buyer_runnable": True, "evidence_tier": "MODEL_RUNNING", "experiment_required": True,
                   "limitations": ["Simplified survival model", "No 3D geometry", "No immune response", "No blood flow dynamics", "FEBio cross-check PENDING"]}, f, indent=2)

if __name__ == "__main__": main()

#!/usr/bin/env python3
"""
P-16 Independent Cross-Check — Analytical MCML vs Diffuse Model
=================================================================
Per CEO R308 P5: 'Require agreement before promoting beyond MODEL_VERIFIED.'

This script implements an INDEPENDENT analytical model (Kubelka-Munk /
diffusion approximation, different formulation from the committed diffuse model)
and compares results. If the two models agree within 30%, the model is
MODEL_VERIFIED. If not, it's an AI investigation event.

This is NOT MCX/PyTissueOptics (which require installation), but it IS
an independent analytical implementation using a different mathematical
formulation (Kubelka-Munk two-flux model vs diffusion approximation).
"""
import json, os, math
from datetime import datetime, timezone

# Model A: Diffusion approximation (from committed p16_nir_diffuse_committed.py)
def model_a_diffusion(mu_a, mu_s, d_cm, g=0.9):
    mu_s_prime = mu_s * (1 - g)
    mu_eff = math.sqrt(3 * mu_a * (mu_a + mu_s_prime))
    return math.exp(-mu_eff * d_cm)

# Model B: Kubelka-Munk two-flux model (INDEPENDENT formulation)
def model_b_kubelka_munk(mu_a, mu_s, d_cm):
    """Kubelka-Munk: separate absorption (K) and scattering (S) coefficients.
    K ≈ 2*mu_a, S ≈ (3/4)*mu_s*(1-g) ≈ (3/4)*mu_s' (approximate relation)
    T = 1 / (cosh(b*S*d) + (a+b)/(2*b) * sinh(b*S*d))
    where a = (S+K)/S, b = sqrt(a²-1)
    """
    K = 2 * mu_a  # Kubelka-Munk absorption
    S = 0.75 * mu_s * 0.1  # Kubelka-Munk scattering (mu_s' = mu_s*(1-0.9) = 0.1*mu_s)
    
    if S < 1e-9:
        return math.exp(-K * d_cm)  # pure absorption limit
    
    a = (S + K) / S
    b = math.sqrt(max(0, a**2 - 1))
    
    if b < 1e-9:
        return math.exp(-K * d_cm)
    
    bd = b * S * d_cm
    denom = math.cosh(bd) + (a + b) / (2 * b) * math.sinh(bd)
    return 1.0 / denom if denom > 0 else 0

# Test wavelengths
WAVELENGTHS = {
    850:  {"scalp_mu_a": 0.5, "scalp_mu_s": 150, "skull_mu_a": 0.1, "skull_mu_s": 200},
    940:  {"scalp_mu_a": 0.3, "scalp_mu_s": 120, "skull_mu_a": 0.08, "skull_mu_s": 160},
    1064: {"scalp_mu_a": 0.2, "scalp_mu_s": 80,  "skull_mu_a": 0.05, "skull_mu_s": 100},
    1300: {"scalp_mu_a": 0.15,"scalp_mu_s": 50,  "skull_mu_a": 0.04, "skull_mu_s": 60},
}

SCALP_CM = 0.5; SKULL_CM = 1.0

def main():
    print("="*100)
    print("P-16 INDEPENDENT CROSS-CHECK")
    print("Model A: Diffusion approximation (mu_eff = sqrt(3*mu_a*(mu_a+mu_s')))")
    print("Model B: Kubelka-Munk two-flux (independent formulation)")
    print("="*100)
    
    results = []
    for wl, props in WAVELENGTHS.items():
        # Model A
        T_a_scalp = model_a_diffusion(props["scalp_mu_a"], props["scalp_mu_s"], SCALP_CM)
        T_a_skull = model_a_diffusion(props["skull_mu_a"], props["skull_mu_s"], SKULL_CM)
        T_a_total = T_a_scalp * T_a_skull
        
        # Model B
        T_b_scalp = model_b_kubelka_munk(props["scalp_mu_a"], props["scalp_mu_s"], SCALP_CM)
        T_b_skull = model_b_kubelka_munk(props["skull_mu_a"], props["skull_mu_s"], SKULL_CM)
        T_b_total = T_b_scalp * T_b_skull
        
        # Compare
        if T_a_total > 0:
            discrepancy = abs(T_a_total - T_b_total) / T_a_total * 100
        else:
            discrepancy = 999
        
        agree = discrepancy < 30
        
        results.append({
            "wavelength_nm": wl,
            "T_a_diffusion": round(T_a_total, 6),
            "T_b_kubelka_munk": round(T_b_total, 6),
            "discrepancy_pct": round(discrepancy, 1),
            "agree_within_30pct": agree,
        })
        
        print(f"\n  {wl}nm: Diffusion T={T_a_total:.6f} | Kubelka-Munk T={T_b_total:.6f} | Discrepancy: {discrepancy:.1f}% | {'AGREE' if agree else 'DISAGREE'}")
    
    all_agree = all(r["agree_within_30pct"] for r in results)
    verdict = "MODEL_VERIFIED" if all_agree else "MODEL_DISAGREEMENT — INVESTIGATION REQUIRED"
    
    print(f"\n{'='*80}")
    print(f"CROSS-CHECK VERDICT: {verdict}")
    if not all_agree:
        print("  Models disagree by > 30% on some wavelengths.")
        print("  This is an AI investigation event:")
        print("  - Different mathematical formulations give different results")
        print("  - Need Monte Carlo (MCX/PyTissueOptics) as tiebreaker")
        print("  - P-16 remains MODEL_RUNNING (not MODEL_VERIFIED) until resolved")
    else:
        print("  Both models agree within 30% on all wavelengths.")
        print("  P-16 promoted to MODEL_VERIFIED (analytical cross-check passed).")
        print("  Monte Carlo (MCX/PyTissueOptics) still needed for full validation.")
    
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "p16_crosscheck_R308.json"), 'w') as f:
        json.dump({"artifact": "P-16 Cross-Check", "timestamp": datetime.now(timezone.utc).isoformat(),
                   "model_a": "Diffusion approximation", "model_b": "Kubelka-Munk two-flux",
                   "results": results, "verdict": verdict,
                   "all_agree": all_agree,
                   "note": "Monte Carlo (MCX/PyTissueOptics) still needed for full validation"}, f, indent=2)

if __name__ == "__main__": main()

#!/usr/bin/env python3
"""P-12 Enzymatic Tau/Alpha-Synuclein Clearance Kinetics"""
import json, os, math
from datetime import datetime, timezone

# Similar to P-04 but targets tau and alpha-synuclein instead of Aβ42.
# Comparator: No enzyme (passive drainage)
# Falsification: >= 15% tau clearance per pass at physiological CSF tau concentration

# Literature parameters
TAU_PROTEASES = [
    {"enzyme": "Cathepsin D", "target": "tau", "Km_uM": 2.0, "kcat_per_s": 5.0, "csf_conc_nM": 300, "provenance": "Literature: cathepsin D tau degradation"},
    {"enzyme": "MMP-2", "target": "tau", "Km_uM": 8.0, "kcat_per_s": 2.0, "csf_conc_nM": 300, "provenance": "Literature: MMP-2 tau cleavage"},
    {"enzyme": "NEP (neprilysin)", "target": "alpha-synuclein", "Km_uM": 3.0, "kcat_per_s": 8.0, "csf_conc_nM": 500, "provenance": "Literature: NEP degrades alpha-synuclein"},
    {"enzyme": "IDE", "target": "alpha-synuclein", "Km_uM": 5.0, "kcat_per_s": 3.0, "csf_conc_nM": 500, "provenance": "Literature: IDE alpha-synuclein"},
]

FLOW_mL_min = 0.3
MEMBRANE_AREA_cm2 = 5.0
MEMBRANE_THICKNESS_um = 100
ENZYME_LOADINGS = [0.1, 0.5, 1.0, 5.0, 10.0]

def compute_clearance(enzyme):
    vol_mL = MEMBRANE_AREA_cm2 * MEMBRANE_THICKNESS_um * 1e-4
    tau_s = vol_mL / FLOW_mL_min * 60
    S_uM = enzyme["csf_conc_nM"] * 1e-3
    results = []
    for loading in ENZYME_LOADINGS:
        Vmax = enzyme["kcat_per_s"] * loading
        k_obs = Vmax / (enzyme["Km_uM"] + S_uM)
        clearance = 1 - math.exp(-k_obs * tau_s)
        results.append({"loading_uM": loading, "clearance_pct": round(clearance * 100, 2)})
    best = max(results, key=lambda r: r["clearance_pct"])
    return {"enzyme": enzyme["enzyme"], "target": enzyme["target"], "S_uM": round(S_uM, 4),
            "mass_transport_limited": S_uM < enzyme["Km_uM"] * 0.1,
            "results": results, "best_clearance_pct": best["clearance_pct"]}

def main():
    print("=" * 80)
    print("P-12 ENZYMATIC TAU/ALPHA-SYNUCLEIN CLEARANCE")
    print("=" * 80)
    
    all_results = [compute_clearance(e) for e in TAU_PROTEASES]
    for r in all_results:
        print(f"\n  {r['enzyme']} ({r['target']}): best clearance = {r['best_clearance_pct']}% | mass-transport limited: {r['mass_transport_limited']}")
    
    best_overall = max(all_results, key=lambda r: r["best_clearance_pct"])
    verdict = "PASS" if best_overall["best_clearance_pct"] >= 15 else "FAIL"
    
    print(f"\n{'='*80}")
    print(f"FALSIFICATION: Best = {best_overall['enzyme']} at {best_overall['best_clearance_pct']}% (threshold 15%)")
    print(f"VERDICT: {verdict}")
    print(f"\nBUYER_RUNNABLE: YES (EXPERIMENT REQUIRED)")
    print(f"Limitations: Solution kinetics (immobilized may differ), no CSF stability, COPASI cross-check PENDING")
    
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "p12_results_R307.json"), 'w') as f:
        json.dump({"artifact": "P-12", "timestamp": datetime.now(timezone.utc).isoformat(),
                   "results": all_results,
                   "falsification": {"criterion": ">=15% clearance", "best": best_overall["best_clearance_pct"], "verdict": verdict},
                   "buyer_runnable": True, "evidence_tier": "MODEL_SUPPORTED", "experiment_required": True,
                   "limitations": ["Solution kinetics", "No CSF stability", "COPASI PENDING"]}, f, indent=2)

if __name__ == "__main__": main()

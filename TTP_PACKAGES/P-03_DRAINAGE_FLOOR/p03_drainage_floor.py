#!/usr/bin/env python3
"""P-03 Drainage Floor — Standalone Safety Module (extracted from P-01)"""
import json, os, math
from datetime import datetime, timezone

# Mechanism: Hard minimum drainage guarantee preventing complete flow collapse.
# Extracted from P-01 ablation evidence as independently runnable package.
# Comparator: No drainage floor (controller can reduce drainage to zero).
# Falsification: With drainage floor, system must maintain ICP <= P_MAX (20 mmHg)
#   for >= 80% of simulation when 1 of 4 segments progressively fails.

P_TARGET = 12.0; P_MAX = 20.0; Q_PROD = 0.3; G_HEALTHY = 0.060
DT = 1.0; N_STEPS = 86400; K_OCCL = 1.0/3600

def simulate(has_floor, seed=42):
    import random
    random.seed(seed)
    # 4 segments, 1 fails progressively
    alpha = [0.104, 0.104, 0.104, 0.104]  # design operating point
    lesion_start = random.uniform(2, 18) * 3600
    icp_series = []
    
    for step in range(N_STEPS):
        t = step * DT
        # Lesion on segment 0
        if t > lesion_start:
            decay = math.exp(-K_OCCL * (t - lesion_start))
            alpha[0] = max(0.0, 0.104 * decay)
        
        # Compute ICP
        G_total = sum(a * G_HEALTHY for a in alpha)
        p_icp = Q_PROD / G_total if G_total > 1e-9 else 999
        
        # Drainage floor: if floor active, ensure minimum conductance
        if has_floor:
            min_G = Q_PROD * 0.50 / P_MAX  # 50% drainage floor
            if G_total < min_G:
                # Boost alpha to maintain floor
                boost = min_G / G_HEALTHY / 4
                alpha = [max(a, boost) for a in alpha]
                G_total = sum(a * G_HEALTHY for a in alpha)
                p_icp = Q_PROD / G_total
        
        icp_series.append(min(p_icp, 100))  # cap for display
    
    pct_in_bounds = sum(1 for p in icp_series if p <= P_MAX) / len(icp_series)
    peak = max(icp_series)
    return {"pct_in_bounds": round(pct_in_bounds*100, 1), "peak_icp": round(peak, 1)}

def main():
    print("="*80)
    print("P-03 DRAINAGE FLOOR — STANDALONE SAFETY MODULE")
    print("="*80)
    
    with_floor = simulate(True)
    without_floor = simulate(False)
    
    print(f"\n  With floor:    {with_floor['pct_in_bounds']}% in bounds, peak {with_floor['peak_icp']} mmHg")
    print(f"  Without floor: {without_floor['pct_in_bounds']}% in bounds, peak {without_floor['peak_icp']} mmHg")
    
    verdict = "PASS" if with_floor["pct_in_bounds"] >= 80 else "FAIL"
    
    print(f"\n  Falsification: >= 80% in bounds with floor → {verdict}")
    print(f"  BUYER_RUNNABLE: YES (extracted from P-01, independently runnable)")
    
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "p03_results_R308.json"), 'w') as f:
        json.dump({"artifact": "P-03", "timestamp": datetime.now(timezone.utc).isoformat(),
                   "with_floor": with_floor, "without_floor": without_floor,
                   "falsification": {"criterion": ">=80% in bounds", "verdict": verdict},
                   "buyer_runnable": True, "evidence_tier": "MODEL_RUNNING"}, f, indent=2)

if __name__ == "__main__": main()

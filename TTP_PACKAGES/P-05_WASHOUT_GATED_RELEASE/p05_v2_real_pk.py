#!/usr/bin/env python3
"""
P-05 V2 — Washout-Gated Drug Release with REAL Pharmacokinetics
================================================================
V1 was TAUTOLOGICAL (flow cancelled by construction). V2 has actual PK:
  - CSF compartment with volume
  - Drug release (fixed-rate or flow-gated)
  - Transport delay
  - Clearance (first-order)
  - Pump response lag
  - Sensor noise
  - Patient variability (flow, clearance, volume)

Comparator: Fixed-rate intrathecal pump.
Falsification: Flow-gated must reduce peak-to-trough concentration variation
  by >= 40% vs fixed-rate across 10 virtual patients.

Run: python p05_v2_real_pk.py
"""
import json, os, math, random
from datetime import datetime, timezone

DT = 1.0  # seconds
N_STEPS = 86400  # 24 hours
DOSE_mg_per_day = 10.0  # 10 mg/day target

def generate_patients():
    random.seed(42)
    patients = []
    for i in range(10):
        patients.append({
            "id": i+1,
            "csf_volume_mL": random.uniform(100, 150),  # CSF compartment volume
            "clearance_rate_per_hr": random.uniform(0.5, 2.0),  # first-order clearance
            "base_flow_mL_min": random.uniform(0.20, 0.40),  # CSF flow
            "diurnal_amp": random.uniform(0.15, 0.35),  # flow variation
            "pump_lag_s": random.uniform(5, 30),  # pump response delay
            "noise_sigma": random.uniform(0.01, 0.05),  # sensor noise (mg/L)
        })
    return patients

def simulate(p, gated=True):
    """Simulate 24h of drug delivery with real PK dynamics."""
    conc = []  # drug concentration in CSF (mg/L)
    c = DOSE_mg_per_day / 24 / 60 / p["csf_volume_mL"]  # initial steady-state
    pump_command = DOSE_mg_per_day / 24 / 60  # mg/min target
    pump_actual = pump_command  # pump output (with lag)
    
    for step in range(N_STEPS):
        t_hr = step * DT / 3600
        
        # CSF flow with diurnal variation
        flow = p["base_flow_mL_min"] * (1 + p["diurnal_amp"] * math.sin(2*math.pi*t_hr/24))
        
        if gated:
            # Flow-gated: release proportional to flow
            target_release = DOSE_mg_per_day / 24 / 60 * (flow / p["base_flow_mL_min"])
        else:
            # Fixed-rate: constant release
            target_release = DOSE_mg_per_day / 24 / 60
        
        # Pump lag (first-order response)
        alpha = 1.0 / max(p["pump_lag_s"], 1.0)
        pump_actual += alpha * (target_release - pump_actual) * DT
        
        # Drug enters CSF compartment
        # dc/dt = (release_rate - clearance - flow_removal) / volume
        clearance_mg_per_min = c * p["clearance_rate_per_hr"] / 60 * p["csf_volume_mL"]
        flow_removal_mg_per_min = c * flow  # drug leaves with CSF flow
        
        dc = (pump_actual - clearance_mg_per_min - flow_removal_mg_per_min) * DT / (p["csf_volume_mL"] * 1e-3)  # mL to L
        c += dc
        
        # Add sensor noise
        c_observed = c + random.gauss(0, p["noise_sigma"])
        c = max(0, c)
        conc.append(max(0, c_observed))
    
    return conc

def compute_variation(series):
    """Peak-to-trough variation as fraction of mean."""
    peak = max(series); trough = min(series); mean = sum(series)/len(series)
    if mean < 1e-9: return 0
    return (peak - trough) / mean

def main():
    print("="*80)
    print("P-05 V2 — WASHOUT-GATED DRUG RELEASE (REAL PK)")
    print("V1 was tautological. V2 has compartment, clearance, lag, noise.")
    print("="*80)
    
    patients = generate_patients()
    results = []
    total_fixed_var = 0; total_gated_var = 0
    
    for p in patients:
        random.seed(42 + p["id"])
        fixed = simulate(p, gated=False)
        random.seed(42 + p["id"])
        gated = simulate(p, gated=True)
        
        fixed_var = compute_variation(fixed)
        gated_var = compute_variation(gated)
        reduction = (fixed_var - gated_var) / fixed_var if fixed_var > 0 else 0
        total_fixed_var += fixed_var
        total_gated_var += gated_var
        
        results.append({
            "patient": p["id"],
            "csf_vol": p["csf_volume_mL"],
            "clearance": p["clearance_rate_per_hr"],
            "flow": p["base_flow_mL_min"],
            "fixed_variation_pct": round(fixed_var * 100, 1),
            "gated_variation_pct": round(gated_var * 100, 1),
            "reduction_pct": round(reduction * 100, 1),
        })
        print(f"  P{p['id']}: vol={p['csf_volume_mL']:.0f}mL cl={p['clearance_rate_per_hr']:.1f}/h flow={p['base_flow_mL_min']:.2f} | Fixed {fixed_var*100:.1f}% → Gated {gated_var*100:.1f}% | Red {reduction*100:.1f}%")
    
    avg_reduction = (total_fixed_var - total_gated_var) / total_fixed_var if total_fixed_var > 0 else 0
    verdict = "PASS" if avg_reduction >= 0.40 else "FAIL"
    
    print(f"\n{'='*80}")
    print(f"FALSIFICATION: avg reduction {avg_reduction*100:.1f}% (threshold 40%)")
    print(f"VERDICT: {verdict}")
    print(f"\nBUYER_RUNNABLE: YES (MODEL_RUNNING — not yet MODEL_VERIFIED)")
    print(f"V1 tautology FIXED. V2 has real PK: compartment, clearance, flow removal, pump lag, noise.")
    print(f"Limitations: Single-compartment PK, no tissue binding, no metabolism, simplified pump.")
    
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "p05_v2_results_R308.json"), 'w') as f:
        json.dump({"artifact": "P-05 V2 Real PK", "timestamp": datetime.now(timezone.utc).isoformat(),
                   "v1_issue": "Tautological — flow cancelled by construction. 0% variation by definition.",
                   "v2_fix": "Real PK: CSF compartment, first-order clearance, flow removal, pump lag, sensor noise",
                   "results": results, "falsification": {"criterion": ">=40% reduction", "actual": round(avg_reduction*100,1), "verdict": verdict},
                   "buyer_runnable": True, "evidence_tier": "MODEL_RUNNING (not MODEL_VERIFIED)",
                   "limitations": ["Single-compartment PK", "No tissue binding", "No metabolism", "Simplified pump dynamics", "COPASI cross-check PENDING"]}, f, indent=2)

if __name__ == "__main__": main()

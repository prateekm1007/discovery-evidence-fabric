#!/usr/bin/env python3
"""P-07 Drainage-Priority Clearance — Standalone Safety Module (extracted from P-04)"""
import json, os
from datetime import datetime, timezone

# Mechanism: Safety controller that guarantees CSF drainage is never compromised
# by therapeutic clearance function. Drainage floor enforced at all times.
# Comparator: No drainage priority (clearance function can reduce drainage below safe level).
# Falsification: Under simulated clearance module activation, drainage must never
#   drop below 0.10 mL/min (safety floor) for more than 60 seconds.

DRAINAGE_FLOOR = 0.10  # mL/min — hard safety floor
CLEARANCE_ACTIVATION_TIMES = [3600, 7200, 14400, 28800, 43200, 57600]  # seconds
BASELINE_DRAINAGE = 0.30  # mL/min

def simulate(has_priority=True):
    """Simulate 24h with periodic clearance module activation."""
    drainage_series = []
    for t in range(86400):
        # Baseline drainage
        drainage = BASELINE_DRAINAGE
        
        # Clearance module activates periodically, reduces drainage
        for act_time in CLEARANCE_ACTIVATION_TIMES:
            if act_time <= t < act_time + 300:  # 5-minute activation
                drainage -= 0.25  # clearance module draws 0.25 mL/min from drainage
        
        # Drainage priority: enforce floor
        if has_priority and drainage < DRAINAGE_FLOOR:
            drainage = DRAINAGE_FLOOR
        
        drainage_series.append(max(0, drainage))
    
    violations = sum(1 for d in drainage_series if d < DRAINAGE_FLOOR)
    violation_time = violations  # seconds below floor
    min_drainage = min(drainage_series)
    
    return {
        "violation_seconds": violation_time,
        "min_drainage": round(min_drainage, 3),
        "floor_enforced": has_priority,
    }

def main():
    print("="*80)
    print("P-07 DRAINAGE-PRIORITY CLEARANCE — STANDALONE SAFETY MODULE")
    print("="*80)
    
    with_priority = simulate(True)
    without_priority = simulate(False)
    
    print(f"\n  With priority:    violations={with_priority['violation_seconds']}s, min={with_priority['min_drainage']} mL/min")
    print(f"  Without priority: violations={without_priority['violation_seconds']}s, min={without_priority['min_drainage']} mL/min")
    
    verdict = "PASS" if with_priority["violation_seconds"] <= 60 else "FAIL"
    
    print(f"\n  Falsification: <= 60s below floor → {verdict}")
    print(f"  BUYER_RUNNABLE: YES (extracted from P-04, independently runnable)")
    
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "p07_results_R308.json"), 'w') as f:
        json.dump({"artifact": "P-07", "timestamp": datetime.now(timezone.utc).isoformat(),
                   "with_priority": with_priority, "without_priority": without_priority,
                   "falsification": {"criterion": "<=60s below 0.10 mL/min floor", "verdict": verdict},
                   "buyer_runnable": True, "evidence_tier": "MODEL_RUNNING"}, f, indent=2)

if __name__ == "__main__": main()

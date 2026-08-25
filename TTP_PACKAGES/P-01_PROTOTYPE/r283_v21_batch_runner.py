#!/usr/bin/env python3
"""V2.1 batch runner — saves incrementally."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
v21 = import_module("14_V2_1_validation")

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = [42, 43, 44, 45, 46]
ATTACKS = v21._v2f.ATTACK_MODES
OUTPUT = os.path.join(HERE, "p01_V2_1_validation_results.json")

def main():
    existing = []
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            existing = json.load(f)
    existing_keys = set((r["seed"], r["attack_mode"]) for r in existing)
    total = len(SEEDS) * len(ATTACKS)
    done = len(existing)
    print(f"V2.1 validation: {done}/{total} done. Running remaining...")

    for attack in ATTACKS:
        for seed in SEEDS:
            key = (seed, attack)
            if key in existing_keys:
                continue
            r = v21.run_v2_1("C_V2", seed, attack)
            existing.append(r)
            existing_keys.add(key)
            done += 1
            if done % 5 == 0:
                print(f"  [{done}/{total}] seed={seed} {attack}: t_fail={r['metric_3_time_to_critical_failure_hr']}h surv={r['survival']}")
                with open(OUTPUT, 'w') as f:
                    json.dump(existing, f, indent=2)

    with open(OUTPUT, 'w') as f:
        json.dump(existing, f, indent=2)
    print(f"COMPLETE: {len(existing)}/{total} runs saved to {OUTPUT}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
R282 Multi-seed batch runner.
Runs V2 vs B (5 seeds × 9 attacks) and ablation (5 seeds × 5 arms × 9 attacks).
Saves results incrementally after each seed so partial results survive interruption.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
v2f = import_module("12_V2_full_validation")

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = [42, 43, 44, 45, 46]
ATTACKS = v2f.ATTACK_MODES

# Primary: V2 vs B
primary_arms = ["B_predictive_closed_loop", "C_V2"]
primary_file = os.path.join(HERE, "p01_R282_primary_V2_vs_B_5seeds.json")

# Ablation: 5 arms
ablation_arms = ["C_V2", "V2_no_rate_limit", "V2_no_hysteresis", "V2_no_drainage_floor", "V2_no_alpha_floor"]
ablation_file = os.path.join(HERE, "p01_R282_ablation_5seeds.json")

def run_batch(arms, seeds, attacks, output_file, label):
    # Load existing results if any
    existing = []
    if os.path.exists(output_file):
        with open(output_file) as f:
            existing = json.load(f)
    existing_keys = set((r["scenario"], r["seed"], r["attack_mode"]) for r in existing)

    total = len(arms) * len(seeds) * len(attacks)
    done = len(existing)
    print(f"[{label}] {done}/{total} already done. Running remaining...")

    for seed in seeds:
        for arm in arms:
            for attack in attacks:
                key = (arm, seed, attack)
                if key in existing_keys:
                    continue
                cfg = v2f.make_cfg(arm, seed, attack)
                r = v2f.run_v2_full(cfg)
                r_dict = r.__dict__ if hasattr(r, '__dict__') else dict(r.__dict__)
                existing.append(r_dict)
                existing_keys.add(key)
                done += 1
                if done % 10 == 0:
                    print(f"  [{label}] {done}/{total}: {arm} seed={seed} {attack}: t_fail={r_dict.get('metric_3_time_to_critical_failure_hr', '?')}h")
                    # Save incrementally
                    with open(output_file, 'w') as f:
                        json.dump(existing, f, indent=2)

    # Final save
    with open(output_file, 'w') as f:
        json.dump(existing, f, indent=2)
    print(f"[{label}] COMPLETE: {len(existing)}/{total} runs saved to {output_file}")
    return existing

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("primary", "all"):
        primary = run_batch(primary_arms, SEEDS, ATTACKS, primary_file, "PRIMARY")
        print(f"\nPrimary results: {len(primary)} runs")

    if mode in ("ablation", "all"):
        ablation = run_batch(ablation_arms, SEEDS, ATTACKS, ablation_file, "ABLATION")
        print(f"\nAblation results: {len(ablation)} runs")

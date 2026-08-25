#!/usr/bin/env python3
"""
R284 P1 — DECISIVE COMMERCIAL COMPARISON: V2.1 vs B
====================================================

CEO R284: "The real commercial question: V2.1 vs B, where B is the
existing predictive closed-loop comparator. Does V2.1 outperform B,
not merely V2?"

4 arms:
  A = conventional (1 segment, fixed valve)
  B = existing predictive closed-loop (4 segments, soft modulation, no rate limit)
  C = V2 (4 segments, rate-limited, NO sensor-health detector)
  D = V2.1 (4 segments, rate-limited + sensor-health-aware safe fallback)

8 attacks (excludes 'none' which is baseline):
  noise_3x, sensor_dropout, fast_occlusion, slow_occlusion,
  wrong_model, controller_delay, actuator_saturation, multi_failure

5 seeds: 42, 43, 44, 45, 46

Total: 4 × 8 × 5 = 160 runs

THE DECISIVE QUESTION: Does V2.1 (D) outperform B?

Run:
    python r284_decisive_comparison.py
"""

import sys, os, json, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module

_v2f = import_module("12_V2_full_validation")
_v21 = import_module("14_V2_1_validation")
_v2mod = import_module("10_V2_comparison")

P_MIN_MMHG = _v2f.P_MIN_MMHG
P_MAX_MMHG = _v2f.P_MAX_MMHG
P_TARGET_MMHG = _v2f.P_TARGET_MMHG
F_MAX_PER_SEG = _v2f.F_MAX_PER_SEG
Q_PRODUCTION_ML_MIN = _v2f.Q_PRODUCTION_ML_MIN
G_HEALTHY = _v2f.G_HEALTHY
DT_SEC = _v2f.DT_SEC
N_STEPS = _v2f.N_STEPS
SENSOR_NOISE_P_SIGMA = _v2f.SENSOR_NOISE_P_SIGMA
SENSOR_NOISE_F_SIGMA = _v2f.SENSOR_NOISE_F_SIGMA
K_OCCL_DEFAULT = _v2f.K_OCCL_DEFAULT

SegmentState = _v2f.SegmentState
estimate_occlusion_probability = _v2f.estimate_occlusion_probability
true_conductance_v2 = _v2f.true_conductance_v2

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "p01_R284_decisive_V21_vs_B.json")

SEEDS = [42, 43, 44, 45, 46]
ATTACKS = ["noise_3x", "sensor_dropout", "fast_occlusion", "slow_occlusion",
           "wrong_model", "controller_delay", "actuator_saturation", "multi_failure"]
ARMS = ["A_simple", "B_predictive_closed_loop", "C_V2", "D_V2_1"]


def run_one(arm, seed, attack):
    """Run one simulation. Returns result dict with 7 metrics."""
    if arm == "D_V2_1":
        # Use V2.1 controller
        return _v21.run_v2_1("C_V2", seed, attack)

    # A, B, C use the V2 full validation framework
    cfg = _v2f.make_cfg(arm, seed, attack)
    r = _v2f.run_v2_full(cfg)
    return {
        "scenario": arm,
        "seed": seed,
        "attack_mode": attack,
        "metric_1_peak_icp_mmhg": r.metric_1_peak_icp_mmhg,
        "metric_2_time_above_threshold_sec": r.metric_2_time_above_threshold_sec,
        "metric_3_time_to_critical_failure_hr": r.metric_3_time_to_critical_failure_hr,
        "metric_4_drainage_preserved_percent": r.metric_4_drainage_preserved_percent,
        "metric_5_false_interventions": r.metric_5_false_interventions,
        "metric_6_actuation_count": r.metric_6_actuation_count,
        "metric_7_energy_arbitrary_units": r.metric_7_energy_arbitrary_units,
        "survival": r.survival,
    }


def main():
    # Load existing
    existing = []
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            existing = json.load(f)
    existing_keys = set((r["scenario"], r["seed"], r["attack_mode"]) for r in existing)

    total = len(ARMS) * len(ATTACKS) * len(SEEDS)
    done = len(existing)
    print(f"R284 DECISIVE COMPARISON: {done}/{total} done. Running remaining...")

    for arm in ARMS:
        for attack in ATTACKS:
            for seed in SEEDS:
                key = (arm, seed, attack)
                if key in existing_keys:
                    continue
                r = run_one(arm, seed, attack)
                # Normalize scenario field
                if "scenario" not in r:
                    r["scenario"] = arm
                r["scenario"] = arm  # force correct arm label
                existing.append(r)
                existing_keys.add(key)
                done += 1
                if done % 10 == 0:
                    print(f"  [{done}/{total}] {arm} seed={seed} {attack}: t_fail={r.get('metric_3_time_to_critical_failure_hr', '?')}h")
                    with open(OUTPUT, 'w') as f:
                        json.dump(existing, f, indent=2)

    with open(OUTPUT, 'w') as f:
        json.dump(existing, f, indent=2)
    print(f"COMPLETE: {len(existing)}/{total} runs saved to {OUTPUT}")

    # Analysis
    print("\n" + "=" * 110)
    print("DECISIVE COMPARISON: V2.1 (D) vs B (existing predictive closed-loop)")
    print("=" * 110)
    print(f"{'Attack':<22} {'B t_fail':<10} {'V2.1 t_fail':<12} {'V2.1/B':<8} {'B peak':<10} {'V2.1 peak':<10} {'V2.1 wins':<10} {'Verdict':<15}")
    print("-" * 110)

    v21_wins = 0
    for attack in ATTACKS:
        b_runs = [r for r in existing if r["scenario"] == "B_predictive_closed_loop" and r["attack_mode"] == attack]
        d_runs = [r for r in existing if r["scenario"] == "D_V2_1" and r["attack_mode"] == attack]
        if not b_runs or not d_runs:
            print(f"{attack:<22} MISSING")
            continue
        b_tfail = sum(r["metric_3_time_to_critical_failure_hr"] for r in b_runs) / len(b_runs)
        d_tfail = sum(r["metric_3_time_to_critical_failure_hr"] for r in d_runs) / len(d_runs)
        b_peak = sum(r["metric_1_peak_icp_mmhg"] for r in b_runs) / len(b_runs)
        d_peak = sum(r["metric_1_peak_icp_mmhg"] for r in d_runs) / len(d_runs)
        ratio = d_tfail / max(b_tfail, 0.01)
        d_wins_seeds = sum(1 for b, d in zip(sorted(b_runs, key=lambda r: r["seed"]),
                                              sorted(d_runs, key=lambda r: r["seed"]))
                          if d["metric_3_time_to_critical_failure_hr"] > b["metric_3_time_to_critical_failure_hr"])
        d_better = (d_tfail > b_tfail * 1.10) and (d_peak <= b_peak * 1.1) and (d_wins_seeds >= 4)
        if d_better:
            verdict = "V2.1 BETTER"
            v21_wins += 1
        elif d_tfail > b_tfail:
            verdict = "V2.1 marginal"
        else:
            verdict = "V2.1 WORSE"
        print(f"{attack:<22} {b_tfail:<10.2f} {d_tfail:<12.2f} {ratio:<8.2f} {b_peak:<10.1f} {d_peak:<10.1f} {d_wins_seeds}/5{'':<5} {verdict:<15}")

    print(f"\nV2.1 materially outperforms B on {v21_wins}/{len(ATTACKS)} attack modes.")

    # Also show V2 vs B for comparison (repair vs incremental)
    print("\n" + "=" * 110)
    print("REPAIR vs INCREMENTAL: V2 vs B (incremental) and V2.1 vs V2 (repair)")
    print("=" * 110)
    print(f"{'Attack':<22} {'B t_fail':<10} {'V2 t_fail':<10} {'V2.1 t_fail':<12} {'V2/B':<8} {'V2.1/B':<8} {'V2.1/V2':<8}")
    print("-" * 110)
    for attack in ATTACKS:
        b_runs = [r for r in existing if r["scenario"] == "B_predictive_closed_loop" and r["attack_mode"] == attack]
        c_runs = [r for r in existing if r["scenario"] == "C_V2" and r["attack_mode"] == attack]
        d_runs = [r for r in existing if r["scenario"] == "D_V2_1" and r["attack_mode"] == attack]
        if not (b_runs and c_runs and d_runs):
            continue
        b_t = sum(r["metric_3_time_to_critical_failure_hr"] for r in b_runs) / len(b_runs)
        c_t = sum(r["metric_3_time_to_critical_failure_hr"] for r in c_runs) / len(c_runs)
        d_t = sum(r["metric_3_time_to_critical_failure_hr"] for r in d_runs) / len(d_runs)
        print(f"{attack:<22} {b_t:<10.2f} {c_t:<10.2f} {d_t:<12.2f} {c_t/max(b_t,0.01):<8.2f} {d_t/max(b_t,0.01):<8.2f} {d_t/max(c_t,0.01):<8.2f}")


if __name__ == "__main__":
    main()

"""
P-01 V2 — Sensor Dropout Failure Characterization (R283 P1)
============================================================

R283 directive: "Do not immediately tune V2.1 and then report a better result.
First characterize the failure."

This script characterizes V2's sensor_dropout failure mechanism by running
a SWEEP of dropout durations to find:
  1. Dropout duration threshold (below which V2 is unaffected, above which it fails)
  2. Controller state during dropout (what does V2 do when sensors read 0?)
  3. Safe fallback state (what SHOULD V2 do during dropout?)
  4. Maximum allowable stale-sensor interval (how long can sensors be stale?)
  5. Why the rate limiter becomes harmful (the specific mechanism)

The characterization is done BEFORE designing V2.1. Per Article XXVIII, we
must understand the failure before proposing a fix.

Run:
    python 13_sensor_dropout_characterization.py
"""

from __future__ import annotations
import argparse, json, math, os, random, sys
from dataclasses import asdict
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_v2f = __import__("12_V2_full_validation")
_v2mod = __import__("10_V2_comparison")

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
true_conductance = _v2f.true_conductance
true_conductance_v2 = _v2f.true_conductance_v2


def run_dropout_sweep(seed: int, dropout_durations_sec: List[float],
                      dropout_interval_sec: float = 600.0) -> List[dict]:
    """
    Run V2 under sensor_dropout with varying dropout durations.
    For each duration, measure: t_fail, peak ICP, controller state during dropout.

    dropout_interval_sec: average time between dropout events (600 = 10 min)
    """
    results = []

    for dropout_dur in dropout_durations_sec:
        random.seed(seed)

        segs = [SegmentState(idx=i, n_segments_total=4) for i in range(4)]
        lesion_times = sorted([random.uniform(2.0, 18.0) for _ in range(2)])
        for t_hr, seg_idx in zip(lesion_times, range(2)):
            segs[seg_idx].lesion_start_sec = t_hr * 3600.0
            segs[seg_idx].occlusion_active = True

        # Dropout state
        dropout_active = False
        dropout_timer = 0.0
        dropout_next = random.uniform(dropout_interval_sec * 0.5, dropout_interval_sec * 1.5)

        # Trackers
        icp_max = float("-inf")
        icp_violation_total = 0.0
        drainage_achieved_ml = 0.0
        drainage_target_ml = Q_PRODUCTION_ML_MIN * (N_STEPS * DT_SEC / 60.0)
        time_to_failure_sec = N_STEPS * DT_SEC
        survival = True

        # Controller state tracking during dropout
        alpha_during_dropout = []  # alpha values while sensors are 0
        alpha_after_dropout = []   # alpha values in the 60s after sensors return
        controller_state_during_dropout = "unknown"

        prev_alpha = [s.alpha for s in segs]
        cfg = _v2f.SimConfigV2Full(scenario="C_V2", seed=seed, attack_mode="sensor_dropout")

        for step in range(N_STEPS):
            t_sec = step * DT_SEC

            for s in segs:
                s.alpha_delayed = s.alpha

            G = [true_conductance_v2(s, t_sec, K_OCCL_DEFAULT, False) for s in segs]
            G_sum = sum(G)
            p_true = Q_PRODUCTION_ML_MIN / G_sum if G_sum > 1e-9 else 10.0 * P_MAX_MMHG
            F_true = [g * p_true for g in G]

            # Sensor with dropout
            if dropout_active:
                p_obs = 0.0
                F_obs = [0.0] * 4
                dropout_timer -= DT_SEC
                if dropout_timer <= 0:
                    dropout_active = False
                    dropout_next = random.uniform(dropout_interval_sec * 0.5, dropout_interval_sec * 1.5)
                    controller_state_during_dropout = "returning"
            else:
                dropout_next -= DT_SEC
                if dropout_next <= 0:
                    dropout_active = True
                    dropout_timer = dropout_dur
                    controller_state_during_dropout = "dropout_start"
                p_obs = p_true + random.gauss(0, SENSOR_NOISE_P_SIGMA)
                F_obs = [f + random.gauss(0, SENSOR_NOISE_F_SIGMA) for f in F_true]

            for i, s in enumerate(segs):
                s.history_F.append(F_obs[i])
                s.history_P.append(p_obs)
                if abs(p_obs) > 1e-3:
                    s.history_G.append(max(0.0, F_obs[i] / p_obs))
                else:
                    s.history_G.append(0.0)

            # V2 controller
            alpha_cmd, _, _ = _v2f.v2_controller_ablated(segs, p_obs, F_obs, cfg, t_sec, _v2f.AblationConfig())

            for i, s in enumerate(segs):
                if not s.isolated:
                    s.alpha = alpha_cmd[i]

            # Track controller state during/after dropout
            if dropout_active:
                alpha_during_dropout.append(list(s.alpha for s in segs))
            elif controller_state_during_dropout == "returning":
                alpha_after_dropout.append(list(s.alpha for s in segs))
                if len(alpha_after_dropout) > 60:
                    controller_state_during_dropout = "normal"

            if p_true > P_MAX_MMHG:
                pass
            icp_max = max(icp_max, p_true)
            if p_true < P_MIN_MMHG or p_true > P_MAX_MMHG:
                icp_violation_total += DT_SEC
            drainage_achieved_ml += sum(F_true) * DT_SEC / 60.0

            if icp_violation_total > 3600:
                survival = False
                time_to_failure_sec = t_sec
                break

        # Analyze controller state during dropout
        if alpha_during_dropout:
            # What did alpha do during dropout? Did it drift toward 0 (fail-safe) or stay?
            first_dropout = alpha_during_dropout[0]
            last_dropout = alpha_during_dropout[-1] if len(alpha_during_dropout) > 1 else first_dropout
            alpha_drift_during_dropout = sum(last_dropout) - sum(first_dropout)
            mean_alpha_during = sum(sum(a) for a in alpha_during_dropout) / len(alpha_during_dropout)
        else:
            alpha_drift_during_dropout = 0.0
            mean_alpha_during = 0.0

        drainage_pct = (drainage_achieved_ml / drainage_target_ml * 100.0) if drainage_target_ml > 0 else 0.0

        results.append({
            "dropout_duration_sec": dropout_dur,
            "seed": seed,
            "t_fail_hr": round(time_to_failure_sec / 3600.0, 2),
            "peak_icp_mmhg": round(icp_max if icp_max != float("-inf") else 0.0, 2),
            "drainage_percent": round(drainage_pct, 1),
            "survival": survival,
            "mean_alpha_during_dropout": round(mean_alpha_during, 4),
            "alpha_drift_during_dropout": round(alpha_drift_during_dropout, 4),
            "num_dropout_events": len(alpha_during_dropout) // max(int(dropout_dur), 1) if dropout_dur > 0 else 0,
        })

    return results


def characterize_failure():
    """Run the dropout duration sweep and characterize the failure."""
    # Sweep dropout durations: 0 (no dropout), 10s, 30s, 60s, 120s, 300s, 600s
    dropout_durations = [0, 10, 30, 60, 120, 300, 600]
    seeds = [42, 43, 44]

    print("=" * 100)
    print("SENSOR DROPOUT FAILURE CHARACTERIZATION")
    print("Question: At what dropout duration does V2 fail, and why?")
    print("=" * 100)

    all_results = []
    for seed in seeds:
        print(f"\n--- Seed {seed} ---")
        results = run_dropout_sweep(seed, dropout_durations)
        all_results.extend(results)
        for r in results:
            print(f"  dropout={r['dropout_duration_sec']:4d}s: t_fail={r['t_fail_hr']:6.2f}h  "
                  f"peak={r['peak_icp_mmhg']:7.1f}  drain={r['drainage_percent']:5.1f}%  "
                  f"surv={'Y' if r['survival'] else 'N'}  "
                  f"alpha_during={r['mean_alpha_during_dropout']:.4f}")

    # Analysis
    print("\n" + "=" * 100)
    print("FAILURE MECHANISM ANALYSIS")
    print("=" * 100)

    # Find threshold: the dropout duration at which V2 first fails
    for seed in seeds:
        seed_results = [r for r in all_results if r["seed"] == seed]
        print(f"\nSeed {seed}:")
        for r in seed_results:
            status = "OK" if r["survival"] else "FAIL"
            print(f"  dropout={r['dropout_duration_sec']:4d}s → {status} (t_fail={r['t_fail_hr']}h, "
                  f"alpha_during_dropout={r['mean_alpha_during_dropout']:.4f})")

    # Aggregate
    print("\n" + "=" * 100)
    print("AGGREGATE FINDINGS (mean across 3 seeds)")
    print("=" * 100)
    print(f"{'Dropout dur (s)':<18} {'Mean t_fail (h)':<18} {'Mean peak':<12} {'Survival rate':<15} {'Mean alpha during':<18}")
    print("-" * 100)
    for dur in dropout_durations:
        dur_results = [r for r in all_results if r["dropout_duration_sec"] == dur]
        if dur_results:
            mean_tfail = sum(r["t_fail_hr"] for r in dur_results) / len(dur_results)
            mean_peak = sum(r["peak_icp_mmhg"] for r in dur_results) / len(dur_results)
            surv_rate = sum(1 for r in dur_results if r["survival"]) / len(dur_results)
            mean_alpha = sum(r["mean_alpha_during_dropout"] for r in dur_results) / len(dur_results)
            print(f"{dur:<18} {mean_tfail:<18.2f} {mean_peak:<12.1f} {surv_rate:<15.2f} {mean_alpha:<18.4f}")

    # Save results
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "p01_sensor_dropout_characterization.json")
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nWrote {len(all_results)} runs to {out}")


if __name__ == "__main__":
    characterize_failure()

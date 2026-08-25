"""
P-01 V2.1 — Sensor-Health-Aware Rate-Limited Controller (R283 P1)
==================================================================

V2.1 = V2 + sensor-health detector + safe fallback.

DESIGN (frozen in V2_1_PRE_REGISTRATION.json BEFORE testing):
  1. Sensor-health detector: if p_obs == 0 OR |p_obs - p_obs_prev| > 50 mmHg, flag UNHEALTHY
  2. Safe fallback: when UNHEALTHY, FREEZE alpha at last known good value
  3. Sensor recovery: when HEALTHY for 3 consecutive samples, gradually unfreeze
  4. All V2 mechanisms preserved

Run:
    python 14_V2_1_validation.py
"""

from __future__ import annotations
import argparse, json, math, os, random, sys
from dataclasses import asdict
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_v2f = __import__("12_V2_full_validation")

P_MIN_MMHG = _v2f.P_MIN_MMHG
P_MAX_MMHG = _v2f.P_MAX_MMHG
P_TARGET_MMHG = _v2f.P_TARGET_MMHG
F_MAX_PER_SEG = _v2f.F_MAX_PER_SEG
Q_PRODUCTION_ML_MIN = _v2f.Q_PRODUCTION_ML_MIN
G_HEALTHY = _v2f.G_HEALTHY
DT_SEC = _v2f.DT_SEC
N_STEPS = _v2f.N_STEPS
SENSOR_NOISE_P_SIGMA = _v2f.SENSOR_NOISE_P_SIGMA
K_OCCL_DEFAULT = _v2f.K_OCCL_DEFAULT

SegmentState = _v2f.SegmentState
estimate_occlusion_probability = _v2f.estimate_occlusion_probability
true_conductance_v2 = _v2f.true_conductance_v2
MAX_ALPHA_RATE_PER_SEC = _v2f.MAX_ALPHA_RATE_PER_SEC
ALPHA_MIN = _v2f.ALPHA_MIN
DRAINAGE_FLOOR_FRACTION = _v2f.DRAINAGE_FLOOR_FRACTION
HYSTERESIS_DEADBAND = _v2f.HYSTERESIS_DEADBAND

# V2.1 sensor-health parameters
SENSOR_HEALTH_JUMP_THRESHOLD_MMHG = 50.0  # impossible jump = sensor error
SENSOR_HEALTH_RECOVERY_CONSECUTIVE = 3     # need 3 consecutive good samples to unfreeze
SENSOR_HEALTH_PLAUSIBLE_RANGE = (0.0, 50.0) # p_obs outside this = sensor error


def v2_1_controller(segs: List[SegmentState],
                    p_obs: float,
                    F_obs: List[float],
                    cfg,
                    t_sec: float,
                    state: dict) -> Tuple[List[float], int, int, bool]:
    """
    V2.1 controller. Adds sensor-health detection + safe fallback to V2.

    state dict tracks:
      - sensor_healthy: bool
      - last_good_alpha: List[float] (alpha to freeze at during dropout)
      - consecutive_good: int (counter for recovery)
      - p_obs_prev: float (for jump detection)

    Returns (alpha_cmd, interventions, false_interventions, sensor_healthy)
    """
    n = len(segs)
    interventions = 0
    false_interventions = 0

    # --- Sensor health detection ---
    p_obs_prev = state.get("p_obs_prev", P_TARGET_MMHG)
    # FIX: p_obs exactly 0.0 is a sensor failure (real ICP is never exactly 0)
    # Also: all F_obs == 0 simultaneously is a sensor failure
    all_flow_zero = all(abs(f) < 1e-9 for f in F_obs)
    sensor_plausible = (p_obs > 0.5) and (p_obs <= 50.0) and not all_flow_zero
    jump_too_large = abs(p_obs - p_obs_prev) > SENSOR_HEALTH_JUMP_THRESHOLD_MMHG
    sensor_healthy = sensor_plausible and not jump_too_large

    state["p_obs_prev"] = p_obs if sensor_healthy else p_obs_prev

    if sensor_healthy:
        state["consecutive_good"] = state.get("consecutive_good", 0) + 1
        if state["consecutive_good"] >= SENSOR_HEALTH_RECOVERY_CONSECUTIVE:
            state["sensor_healthy"] = True
    else:
        state["consecutive_good"] = 0
        state["sensor_healthy"] = False

    sensor_currently_healthy = state.get("sensor_healthy", True)

    # --- Safe fallback: if sensor unhealthy, FREEZE alpha ---
    if not sensor_currently_healthy:
        # Freeze alpha at last known good value
        last_good = state.get("last_good_alpha", [s.alpha for s in segs])
        alpha_cmd = list(last_good)
        return alpha_cmd, 0, 0, False

    # --- Sensor healthy: run normal V2 controller ---
    # Save current alpha as "last good" before updating
    state["last_good_alpha"] = [s.alpha for s in segs]

    # Layer 1: Risk estimation
    p_occl = [estimate_occlusion_probability(s, 0.0) for s in segs]

    # Layer 2: Risk-aware allocation (same as V2)
    weights = [(1.0 - p_occl[i]) ** 2 for i in range(n)]
    total_weight = sum(weights)

    K_p = 0.020
    g_total_target = (Q_PRODUCTION_ML_MIN / P_TARGET_MMHG) + K_p * (p_obs - P_TARGET_MMHG)
    g_total_min = Q_PRODUCTION_ML_MIN / P_MAX_MMHG
    g_total_max = Q_PRODUCTION_ML_MIN / P_MIN_MMHG
    g_total_target = max(g_total_min, min(g_total_max, g_total_target))

    if p_obs > 0.1:
        alpha_inv2_cap = F_MAX_PER_SEG / (G_HEALTHY * p_obs)
    else:
        alpha_inv2_cap = 1.0
    alpha_inv2_cap = max(0.0, min(1.0, alpha_inv2_cap))

    alpha_desired = [ALPHA_MIN] * n
    if total_weight > 1e-9:
        for i in range(n):
            share = weights[i] / total_weight
            alpha_desired[i] = max(ALPHA_MIN,
                                   min(alpha_inv2_cap,
                                       share * g_total_target / G_HEALTHY))
    else:
        alpha_per = g_total_target / (G_HEALTHY * n)
        for i in range(n):
            alpha_desired[i] = max(ALPHA_MIN, min(alpha_inv2_cap, alpha_per))

    # Layer 3: Drainage floor (same as V2)
    current_total_G = sum(alpha_desired[i] * G_HEALTHY for i in range(n))
    drainage_predicted = current_total_G * max(p_obs, 0.1)
    drainage_floor = Q_PRODUCTION_ML_MIN * DRAINAGE_FLOOR_FRACTION
    if drainage_predicted < drainage_floor and current_total_G > 1e-9:
        scale_factor = (drainage_floor / max(p_obs, 0.1)) / current_total_G
        for i in range(n):
            alpha_desired[i] = min(alpha_inv2_cap, alpha_desired[i] * scale_factor)

    # Layer 4: Rate limiting + hysteresis (same as V2)
    alpha_cmd = [0.0] * n
    for i, s in enumerate(segs):
        desired = alpha_desired[i]
        current = s.alpha
        if abs(desired - current) < HYSTERESIS_DEADBAND:
            alpha_cmd[i] = current
        else:
            max_change = MAX_ALPHA_RATE_PER_SEC * DT_SEC
            delta = desired - current
            delta = max(-max_change, min(max_change, delta))
            alpha_cmd[i] = current + delta

        if cfg.attack_mode == "actuator_saturation":
            alpha_cmd[i] = min(alpha_cmd[i], 0.70)

    return alpha_cmd, 0, 0, True


def run_v2_1(scenario: str, seed: int, attack: str) -> dict:
    """Run V2.1 simulation."""
    random.seed(seed)

    # Apply attack modes (same as V2)
    k_occl = K_OCCL_DEFAULT
    sensor_noise_mult = 1.0
    wrong_model = False
    controller_delay = 1.0
    n_lesions = 2
    n_segments = 4

    if attack == "noise_2x": sensor_noise_mult = 2.0
    elif attack == "noise_3x": sensor_noise_mult = 3.0
    elif attack == "fast_occlusion": k_occl = 5.0 * K_OCCL_DEFAULT
    elif attack == "slow_occlusion": k_occl = 0.2 * K_OCCL_DEFAULT
    elif attack == "wrong_model": wrong_model = True
    elif attack == "multi_failure": n_lesions = n_segments
    elif attack == "controller_delay": controller_delay = 5.0

    noise_p = SENSOR_NOISE_P_SIGMA * sensor_noise_mult
    noise_f = _v2f.SENSOR_NOISE_F_SIGMA * sensor_noise_mult

    delay_steps = max(1, int(controller_delay / DT_SEC))
    alpha_history = []

    segs = [SegmentState(idx=i, n_segments_total=n_segments) for i in range(n_segments)]
    lesion_times = sorted([random.uniform(2.0, 18.0) for _ in range(n_lesions)])
    for t_hr, seg_idx in zip(lesion_times, range(n_lesions)):
        segs[seg_idx].lesion_start_sec = t_hr * 3600.0
        segs[seg_idx].occlusion_active = True

    # V2.1 controller state
    ctrl_state = {"sensor_healthy": True, "last_good_alpha": [0.104]*4, "consecutive_good": 3, "p_obs_prev": P_TARGET_MMHG}

    icp_max = float("-inf")
    icp_violation_total = 0.0
    drainage_achieved_ml = 0.0
    drainage_target_ml = Q_PRODUCTION_ML_MIN * (N_STEPS * DT_SEC / 60.0)
    time_to_failure_sec = N_STEPS * DT_SEC
    survival = True

    dropout_active = False
    dropout_timer = 0.0
    dropout_next = random.uniform(300, 900)

    cfg = _v2f.SimConfigV2Full(scenario=scenario, seed=seed, attack_mode=attack)

    for step in range(N_STEPS):
        t_sec = step * DT_SEC

        if len(alpha_history) >= delay_steps:
            delayed = alpha_history[-delay_steps]
        else:
            delayed = [s.alpha for s in segs]
        for i, s in enumerate(segs):
            s.alpha_delayed = delayed[i]

        G = [true_conductance_v2(s, t_sec, k_occl, wrong_model) for s in segs]
        G_sum = sum(G)
        p_true = Q_PRODUCTION_ML_MIN / G_sum if G_sum > 1e-9 else 10.0 * P_MAX_MMHG
        F_true = [g * p_true for g in G]

        # Sensor with dropout
        if attack == "sensor_dropout":
            if dropout_active:
                p_obs = 0.0
                F_obs = [0.0] * n_segments
                dropout_timer -= DT_SEC
                if dropout_timer <= 0:
                    dropout_active = False
                    dropout_next = random.uniform(300, 900)
            else:
                dropout_next -= DT_SEC
                if dropout_next <= 0:
                    dropout_active = True
                    dropout_timer = 60.0
                p_obs = p_true + random.gauss(0, noise_p)
                F_obs = [f + random.gauss(0, noise_f) for f in F_true]
        elif sensor_noise_mult > 1 or attack != "none":
            p_obs = p_true + random.gauss(0, noise_p)
            F_obs = [f + random.gauss(0, noise_f) for f in F_true]
        else:
            p_obs = p_true
            F_obs = list(F_true)

        for i, s in enumerate(segs):
            s.history_F.append(F_obs[i])
            s.history_P.append(p_obs)
            if abs(p_obs) > 1e-3:
                s.history_G.append(max(0.0, F_obs[i] / p_obs))
            else:
                s.history_G.append(0.0)

        # V2.1 controller
        alpha_cmd, _, _, sensor_healthy = v2_1_controller(segs, p_obs, F_obs, cfg, t_sec, ctrl_state)

        for i, s in enumerate(segs):
            if not s.isolated:
                s.alpha = alpha_cmd[i]
            else:
                s.alpha = 0.0

        alpha_history.append([s.alpha for s in segs])

        icp_max = max(icp_max, p_true)
        if p_true < P_MIN_MMHG or p_true > P_MAX_MMHG:
            icp_violation_total += DT_SEC
        drainage_achieved_ml += sum(F_true) * DT_SEC / 60.0

        if icp_violation_total > 3600:
            survival = False
            time_to_failure_sec = t_sec
            break

    drainage_pct = (drainage_achieved_ml / drainage_target_ml * 100.0) if drainage_target_ml > 0 else 0.0
    return {
        "scenario": scenario, "seed": seed, "attack_mode": attack,
        "metric_3_time_to_critical_failure_hr": round(time_to_failure_sec / 3600.0, 2),
        "metric_1_peak_icp_mmhg": round(icp_max if icp_max != float("-inf") else 0.0, 2),
        "metric_4_drainage_preserved_percent": round(drainage_pct, 1),
        "survival": survival,
    }


def main():
    seeds = [42, 43, 44, 45, 46]
    attacks = _v2f.ATTACK_MODES

    print("=" * 100)
    print("V2.1 VALIDATION — Sensor-Health-Aware Rate-Limited Controller")
    print("Pre-registered criteria in V2_1_PRE_REGISTRATION.json")
    print("=" * 100)

    all_results = []
    for attack in attacks:
        print(f"\n--- {attack} ---")
        for seed in seeds:
            r = run_v2_1("C_V2", seed, attack)
            all_results.append(r)
            print(f"  seed={seed}: t_fail={r['metric_3_time_to_critical_failure_hr']:6.2f}h  "
                  f"peak={r['metric_1_peak_icp_mmhg']:7.1f}  drain={r['metric_4_drainage_preserved_percent']:5.1f}%  "
                  f"surv={'Y' if r['survival'] else 'N'}")

    # Evaluate pre-registered criteria
    print("\n" + "=" * 100)
    print("PRE-REGISTERED CRITERIA EVALUATION")
    print("=" * 100)

    # C1: sensor_dropout t_fail >= 20h
    dropout_results = [r for r in all_results if r["attack_mode"] == "sensor_dropout"]
    dropout_tfail = sum(r["metric_3_time_to_critical_failure_hr"] for r in dropout_results) / len(dropout_results)
    c1 = dropout_tfail >= 20.0
    print(f"C1: V2.1 sensor_dropout t_fail >= 20h → {dropout_tfail:.2f}h → {'PASS' if c1 else 'FAIL'}")

    # C2: wins >= 4/5 seeds on sensor_dropout
    # Compare to V2 sensor_dropout (from R282: V2 mean 7.51h)
    v2_dropout_tfail = 7.51
    wins = sum(1 for r in dropout_results if r["metric_3_time_to_critical_failure_hr"] > v2_dropout_tfail)
    c2 = wins >= 4
    print(f"C2: V2.1 wins >= 4/5 seeds vs V2 ({v2_dropout_tfail}h) → {wins}/5 → {'PASS' if c2 else 'FAIL'}")

    # C3: peak <= 25 mmHg in all seeds
    max_peak = max(r["metric_1_peak_icp_mmhg"] for r in dropout_results)
    c3 = max_peak <= 25.0
    print(f"C3: V2.1 peak <= 25mmHg → max={max_peak:.1f} → {'PASS' if c3 else 'FAIL'}")

    # C4: no regression on noise_3x (>= 20h)
    noise3_results = [r for r in all_results if r["attack_mode"] == "noise_3x"]
    noise3_tfail = sum(r["metric_3_time_to_critical_failure_hr"] for r in noise3_results) / len(noise3_results)
    c4 = noise3_tfail >= 20.0
    print(f"C4: V2.1 noise_3x t_fail >= 20h → {noise3_tfail:.2f}h → {'PASS' if c4 else 'FAIL'}")

    # C5: no regression on other 7 attacks (>= 80% of V2)
    v2_results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p01_R282_primary_V2_vs_B_5seeds.json")
    v2_data = json.load(open(v2_results_path))
    c5 = True
    print(f"C5: V2.1 >= 80% of V2 on 7 other attacks:")
    for attack in attacks:
        if attack in ("sensor_dropout", "noise_3x"):
            continue
        v2_attack = [r for r in v2_data if r["scenario"] == "C_V2" and r["attack_mode"] == attack]
        v21_attack = [r for r in all_results if r["attack_mode"] == attack]
        if v2_attack and v21_attack:
            v2_mean = sum(r["metric_3_time_to_critical_failure_hr"] for r in v2_attack) / len(v2_attack)
            v21_mean = sum(r["metric_3_time_to_critical_failure_hr"] for r in v21_attack) / len(v21_attack)
            pct = v21_mean / max(v2_mean, 0.01) * 100
            ok = pct >= 80
            if not ok: c5 = False
            print(f"  {attack}: V2={v2_mean:.2f}h V2.1={v21_mean:.2f}h ({pct:.0f}%) → {'OK' if ok else 'REGRESSION'}")

    print(f"\n{'='*50}")
    all_pass = c1 and c2 and c3 and c4 and c5
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    if all_pass:
        print("V2.1 is validated. Replaces V2 as candidate.")
    else:
        print("V2.1 does NOT pass. V2 stays with documented sensor_dropout weakness.")

    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "p01_V2_1_validation_results.json")
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nWrote {len(all_results)} runs to {out}")


if __name__ == "__main__":
    main()

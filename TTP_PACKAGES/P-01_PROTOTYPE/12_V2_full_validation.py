"""
P-01 V2 — Full Robustness + Ablation Matrix (R281)
====================================================

R281 directive: "Do not change the controller before completing the attack.
Run 5+ seeds × A/B/C/D × 9 attacks. Then ablate each V2 mechanism."

This file extends 10_V2_comparison.py with:
  1. All 9 attack modes (adds controller_delay to the 8 from R280)
  2. 4 ablation arms (V2 with each mechanism removed)
  3. 8 metrics (adds false_interventions, failure_severity)

DECISIVE COMPARISON: V2 vs D (existing closed-loop), NOT V2 vs A.
Oracle (D_oracle) only as upper bound, not competitor.

ABLATION ARMS:
  V2_no_rate_limit    — rate limiting disabled (alpha can jump instantly)
  V2_no_hysteresis    — hysteresis deadband set to 0
  V2_no_drainage_floor — drainage floor set to 0 (no minimum drainage protection)
  V2_no_alpha_floor   — alpha floor set to 0 (hard isolation allowed)

Constitutional basis:
- Article XXX: simulator NOT tuned. Same physics as R280.
- Article XXXI: R280 V2 preserved at commit d3d50d1.
- Article XXVIII: ablation determines which mechanism earns the claim.

Run:
    python 12_V2_full_validation.py
    python 12_V2_full_validation.py --seeds 42 43 44 45 46 --arms all
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple

# Import V2 physics and helpers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_v2mod = __import__("10_V2_comparison")

P_MIN_MMHG = _v2mod.P_MIN_MMHG
P_MAX_MMHG = _v2mod.P_MAX_MMHG
P_TARGET_MMHG = _v2mod.P_TARGET_MMHG
F_MAX_PER_SEG = _v2mod.F_MAX_PER_SEG
Q_PRODUCTION_ML_MIN = _v2mod.Q_PRODUCTION_ML_MIN
G_HEALTHY = _v2mod.G_HEALTHY
DT_SEC = _v2mod.DT_SEC
N_STEPS = _v2mod.N_STEPS
SENSOR_NOISE_P_SIGMA = _v2mod.SENSOR_NOISE_P_SIGMA
SENSOR_NOISE_F_SIGMA = _v2mod.SENSOR_NOISE_F_SIGMA
K_OCCL_DEFAULT = _v2mod.K_OCCL_DEFAULT

SegmentState = _v2mod.SegmentState
estimate_occlusion_probability = _v2mod.estimate_occlusion_probability
true_conductance = _v2mod.true_conductance
true_conductance_v2 = _v2mod.true_conductance_v2

# V2 mechanism parameters (from R280)
MAX_ALPHA_RATE_PER_SEC = _v2mod.MAX_ALPHA_RATE_PER_SEC
ALPHA_MIN = _v2mod.ALPHA_MIN
DRAINAGE_FLOOR_FRACTION = _v2mod.DRAINAGE_FLOOR_FRACTION
HYSTERESIS_DEADBAND = _v2mod.HYSTERESIS_DEADBAND


# ---------------------------------------------------------------------------
# Ablation config: V2 with one mechanism removed
# ---------------------------------------------------------------------------

@dataclass
class AblationConfig:
    """Flags to enable/disable each V2 mechanism for ablation study."""
    enable_rate_limit: bool = True
    enable_hysteresis: bool = True
    enable_drainage_floor: bool = True
    enable_alpha_floor: bool = True


# ---------------------------------------------------------------------------
# V2 controller with ablation flags
# ---------------------------------------------------------------------------

def v2_controller_ablated(segs: List[SegmentState],
                          p_obs: float,
                          F_obs: List[float],
                          cfg: 'SimConfigV2Full',
                          t_sec: float,
                          abl: AblationConfig) -> Tuple[List[float], int, int]:
    """
    V2 controller with ablation flags. Returns (alpha_cmd, interventions, false_interventions).

    false_interventions = alpha changes > 0.05 that occurred when the segment
    was NOT actually occluding (lesion_start_sec > t_sec or no lesion).
    This counts predictor false positives.
    """
    n = len(segs)
    interventions = 0
    false_interventions = 0

    # Layer 1: Risk estimation
    p_occl = [estimate_occlusion_probability(s, 0.0) for s in segs]

    # Determine alpha floor
    alpha_floor = ALPHA_MIN if abl.enable_alpha_floor else 0.0

    # Layer 2: Risk-aware allocation
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

    alpha_desired = [alpha_floor] * n
    if total_weight > 1e-9:
        for i in range(n):
            share = weights[i] / total_weight
            alpha_desired[i] = max(alpha_floor,
                                   min(alpha_inv2_cap,
                                       share * g_total_target / G_HEALTHY))
    else:
        alpha_per = g_total_target / (G_HEALTHY * n)
        for i in range(n):
            alpha_desired[i] = max(alpha_floor, min(alpha_inv2_cap, alpha_per))

    # Layer 3: Drainage floor protection
    if abl.enable_drainage_floor:
        current_total_G = sum(alpha_desired[i] * G_HEALTHY for i in range(n))
        drainage_predicted = current_total_G * max(p_obs, 0.1)
        drainage_floor = Q_PRODUCTION_ML_MIN * DRAINAGE_FLOOR_FRACTION
        if drainage_predicted < drainage_floor and current_total_G > 1e-9:
            scale_factor = (drainage_floor / max(p_obs, 0.1)) / current_total_G
            for i in range(n):
                alpha_desired[i] = min(alpha_inv2_cap, alpha_desired[i] * scale_factor)

    # Layer 4: Rate limiting + hysteresis
    hysteresis_deadband = HYSTERESIS_DEADBAND if abl.enable_hysteresis else 0.0
    max_rate = MAX_ALPHA_RATE_PER_SEC if abl.enable_rate_limit else 1.0  # 1.0 = no limit

    alpha_cmd = [0.0] * n
    for i, s in enumerate(segs):
        desired = alpha_desired[i]
        current = s.alpha

        if abs(desired - current) < hysteresis_deadband:
            alpha_cmd[i] = current
        else:
            max_change = max_rate * DT_SEC
            delta = desired - current
            delta = max(-max_change, min(max_change, delta))
            alpha_cmd[i] = current + delta

        if cfg.attack_mode == "actuator_saturation":
            alpha_cmd[i] = min(alpha_cmd[i], 0.70)

        # Count false interventions: significant alpha change on non-occluding segment
        if abs(alpha_cmd[i] - current) > 0.05:
            if not segs[i].occlusion_active or t_sec < segs[i].lesion_start_sec:
                false_interventions += 1

    return alpha_cmd, interventions, false_interventions


# ---------------------------------------------------------------------------
# Extended config with controller_delay attack
# ---------------------------------------------------------------------------

@dataclass
class SimConfigV2Full:
    n_segments: int = 4
    seed: int = 42
    scenario: str = "C_V2"
    k_occl: float = K_OCCL_DEFAULT
    lesion_onset_window_hr: tuple = (2.0, 18.0)
    n_lesions: int = 2
    sensor_noise: bool = True
    actuator_delay: bool = True
    attack_mode: str = "none"
    sensor_noise_multiplier: float = 1.0
    wrong_model: bool = False
    controller_delay_sec: float = 1.0  # default 1s; controller_delay attack = 5s
    ablation: AblationConfig = field(default_factory=AblationConfig)


# ---------------------------------------------------------------------------
# Extended result with 8 metrics
# ---------------------------------------------------------------------------

@dataclass
class SimResultV2Full:
    scenario: str
    seed: int
    attack_mode: str
    # 8 metrics per CEO R281
    metric_1_peak_icp_mmhg: float
    metric_2_time_above_threshold_sec: float
    metric_3_time_to_critical_failure_hr: float
    metric_4_drainage_preserved_percent: float
    metric_5_false_interventions: int
    metric_6_actuation_count: int
    metric_7_energy_arbitrary_units: float
    metric_8_failure_severity: float  # 0-1 scale, 0=no failure, 1=catastrophic
    # Diagnostics
    invariant_1_held: bool
    invariant_2_held: bool
    survival: bool
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Full simulation loop
# ---------------------------------------------------------------------------

def run_v2_full(cfg: SimConfigV2Full) -> SimResultV2Full:
    random.seed(cfg.seed)

    # Apply attack modes
    if cfg.attack_mode == "noise_2x":
        cfg.sensor_noise_multiplier = 2.0
    elif cfg.attack_mode == "noise_3x":
        cfg.sensor_noise_multiplier = 3.0
    elif cfg.attack_mode == "fast_occlusion":
        cfg.k_occl = 5.0 * K_OCCL_DEFAULT
    elif cfg.attack_mode == "slow_occlusion":
        cfg.k_occl = 0.2 * K_OCCL_DEFAULT
    elif cfg.attack_mode == "wrong_model":
        cfg.wrong_model = True
    elif cfg.attack_mode == "multi_failure":
        cfg.n_lesions = cfg.n_segments
    elif cfg.attack_mode == "controller_delay":
        cfg.controller_delay_sec = 5.0  # 5x normal delay

    noise_p = SENSOR_NOISE_P_SIGMA * cfg.sensor_noise_multiplier
    noise_f = SENSOR_NOISE_F_SIGMA * cfg.sensor_noise_multiplier

    # Convert controller delay to steps
    delay_steps = max(1, int(cfg.controller_delay_sec / DT_SEC))
    alpha_history = []  # ring buffer for delayed alpha

    segs = [SegmentState(idx=i, n_segments_total=cfg.n_segments) for i in range(cfg.n_segments)]

    lesion_times = sorted(random.uniform(cfg.lesion_onset_window_hr[0],
                                         cfg.lesion_onset_window_hr[1])
                          for _ in range(cfg.n_lesions))
    for t_hr, seg_idx in zip(lesion_times, range(cfg.n_lesions)):
        segs[seg_idx].lesion_start_sec = t_hr * 3600.0
        segs[seg_idx].occlusion_active = True

    # Trackers
    icp_max = float("-inf")
    icp_min = float("inf")
    time_above_threshold_sec = 0.0
    drainage_achieved_ml = 0.0
    drainage_target_ml = Q_PRODUCTION_ML_MIN * (N_STEPS * DT_SEC / 60.0)
    time_to_critical_failure_sec = N_STEPS * DT_SEC
    false_interventions_total = 0
    actuation_count = 0
    energy_total = 0.0  # sum of |alpha changes|
    prev_alpha = [s.alpha for s in segs]

    icp_violation_total = 0.0
    overload_events = 0
    in_overload = [False] * cfg.n_segments
    in_icp_violation = False

    dropout_active = False
    dropout_timer = 0
    dropout_next = random.uniform(300, 900)

    survival = True
    notes: List[str] = []

    for step in range(N_STEPS):
        t_sec = step * DT_SEC

        # Apply controller delay: alpha_delayed = alpha from delay_steps ago
        if len(alpha_history) >= delay_steps:
            delayed_alphas = alpha_history[-delay_steps]
        else:
            delayed_alphas = [s.alpha for s in segs]  # use current if history too short

        for i, s in enumerate(segs):
            s.alpha_delayed = delayed_alphas[i]

        # Plant step
        G = [true_conductance_v2(s, t_sec, cfg.k_occl, cfg.wrong_model) for s in segs]
        G_sum = sum(G)
        if G_sum <= 1e-9:
            p_true = 10.0 * P_MAX_MMHG
        else:
            p_true = Q_PRODUCTION_ML_MIN / G_sum
        F_true = [g * p_true for g in G]

        # Sensor with dropout
        if cfg.attack_mode == "sensor_dropout":
            if dropout_active:
                p_obs = 0.0
                F_obs = [0.0] * cfg.n_segments
                dropout_timer -= DT_SEC
                if dropout_timer <= 0:
                    dropout_active = False
                    dropout_next = random.uniform(300, 900)
            else:
                dropout_next -= DT_SEC
                if dropout_next <= 0:
                    dropout_active = True
                    dropout_timer = 60.0
                if cfg.sensor_noise:
                    p_obs = p_true + random.gauss(0, noise_p)
                    F_obs = [f + random.gauss(0, noise_f) for f in F_true]
                else:
                    p_obs, F_obs = p_true, list(F_true)
        elif cfg.sensor_noise:
            p_obs = p_true + random.gauss(0, noise_p)
            F_obs = [f + random.gauss(0, noise_f) for f in F_true]
        else:
            p_obs, F_obs = p_true, list(F_true)

        for i, s in enumerate(segs):
            s.history_F.append(F_obs[i])
            s.history_P.append(p_obs)
            if abs(p_obs) > 1e-3:
                s.history_G.append(max(0.0, F_obs[i] / p_obs))
            else:
                s.history_G.append(0.0)

        # Controller dispatch
        if cfg.scenario in ("C_V2", "V2_no_rate_limit", "V2_no_hysteresis",
                            "V2_no_drainage_floor", "V2_no_alpha_floor"):
            alpha_cmd, _, false_intv = v2_controller_ablated(segs, p_obs, F_obs, cfg, t_sec, cfg.ablation)
            false_interventions_total += false_intv
        elif cfg.scenario == "D_oracle_continuous":
            alpha_cmd, _, _ = v2_controller_ablated(segs, p_obs, F_obs, cfg, t_sec, AblationConfig())
            # Oracle uses true conductance for allocation (override)
            true_G_now = [true_conductance_v2(s, t_sec, cfg.k_occl, cfg.wrong_model) for s in segs]
            total_true_G = sum(true_G_now)
            if total_true_G > 1e-9:
                if p_obs > 0.1:
                    alpha_inv2_cap = F_MAX_PER_SEG / (G_HEALTHY * p_obs)
                else:
                    alpha_inv2_cap = 1.0
                alpha_inv2_cap = max(0.0, min(1.0, alpha_inv2_cap))
                K_p = 0.020
                g_total_target = (Q_PRODUCTION_ML_MIN / P_TARGET_MMHG) + K_p * (p_obs - P_TARGET_MMHG)
                for i in range(len(segs)):
                    share = true_G_now[i] / total_true_G
                    desired = max(ALPHA_MIN, min(alpha_inv2_cap, share * g_total_target / G_HEALTHY))
                    current = segs[i].alpha
                    if abs(desired - current) < HYSTERESIS_DEADBAND:
                        alpha_cmd[i] = current
                    else:
                        max_change = MAX_ALPHA_RATE_PER_SEC * DT_SEC
                        delta = max(-max_change, min(max_change, desired - current))
                        alpha_cmd[i] = current + delta
        elif cfg.scenario == "B_predictive_closed_loop":
            v12_cfg = _v2mod._v12.SimConfigV12(
                n_segments=cfg.n_segments, seed=cfg.seed,
                scenario="D_predictive_closed_loop",
                k_occl=cfg.k_occl, lesion_onset_window_hr=cfg.lesion_onset_window_hr,
                n_lesions=cfg.n_lesions, sensor_noise=cfg.sensor_noise,
                actuator_delay=cfg.actuator_delay, isolation_mode="none", attack_mode="none")
            alpha_cmd, _ = _v2mod._v12.arm_d_allocator(segs, p_obs, F_obs, v12_cfg)
        else:  # A_simple
            alpha_cmd = [1.0] * cfg.n_segments

        # Apply alpha
        for i, s in enumerate(segs):
            if not s.isolated:
                s.alpha = alpha_cmd[i]
            else:
                s.alpha = 0.0

            # Count actuations (any change > 0.005)
            change = abs(s.alpha - prev_alpha[i])
            if change > 0.005:
                actuation_count += 1
            energy_total += change  # energy proxy: total alpha movement
            prev_alpha[i] = s.alpha

        # Store alpha history for delay
        alpha_history.append([s.alpha for s in segs])

        # Metrics
        icp_max = max(icp_max, p_true)
        icp_min = min(icp_min, p_true)
        if p_true > P_MAX_MMHG:
            time_above_threshold_sec += DT_SEC
        actual_drainage = sum(F_true) * DT_SEC / 60.0
        drainage_achieved_ml += actual_drainage

        if p_true < P_MIN_MMHG or p_true > P_MAX_MMHG:
            if not in_icp_violation:
                in_icp_violation = True
            icp_violation_total += DT_SEC
        else:
            in_icp_violation = False

        for i, s in enumerate(segs):
            if not s.isolated and F_true[i] > F_MAX_PER_SEG + 1e-6:
                if not in_overload[i]:
                    overload_events += 1
                    in_overload[i] = True
            else:
                in_overload[i] = False

        if all(s.isolated for s in segs):
            survival = False
            time_to_critical_failure_sec = t_sec
            notes.append(f"t={t_sec/3600:.2f}h: all segments isolated")
            break
        if icp_violation_total > 3600:
            survival = False
            time_to_critical_failure_sec = t_sec
            notes.append(f"t={t_sec/3600:.2f}h: ICP out of band >1hr")
            break

    # Compute final metrics
    drainage_pct = (drainage_achieved_ml / drainage_target_ml * 100.0) if drainage_target_ml > 0 else 0.0
    t_fail_hr = time_to_critical_failure_sec / 3600.0
    energy_per_hr = energy_total / (N_STEPS * DT_SEC / 3600.0) if N_STEPS > 0 else 0.0

    # Failure severity: 0 = survived, 1 = catastrophic
    # Based on peak ICP and whether system survived
    if survival:
        failure_severity = max(0.0, (icp_max - P_TARGET_MMHG) / (P_MAX_MMHG - P_TARGET_MMHG)) * 0.5  # max 0.5 if survived
    else:
        failure_severity = 0.5 + min(0.5, (icp_max - P_MAX_MMHG) / (10.0 * P_MAX_MMHG))  # 0.5-1.0 if failed

    return SimResultV2Full(
        scenario=cfg.scenario,
        seed=cfg.seed,
        attack_mode=cfg.attack_mode,
        metric_1_peak_icp_mmhg=round(icp_max if icp_max != float("-inf") else 0.0, 2),
        metric_2_time_above_threshold_sec=round(time_above_threshold_sec, 1),
        metric_3_time_to_critical_failure_hr=round(t_fail_hr, 2),
        metric_4_drainage_preserved_percent=round(drainage_pct, 1),
        metric_5_false_interventions=false_interventions_total,
        metric_6_actuation_count=actuation_count,
        metric_7_energy_arbitrary_units=round(energy_per_hr, 2),
        metric_8_failure_severity=round(failure_severity, 3),
        invariant_1_held=(icp_violation_total == 0),
        invariant_2_held=(overload_events == 0),
        survival=survival,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Scenario presets
# ---------------------------------------------------------------------------

ARMS = {
    "A_simple": {"n_segments": 1, "n_lesions": 1, "ablation": AblationConfig()},
    "B_predictive_closed_loop": {"n_segments": 4, "n_lesions": 2, "ablation": AblationConfig()},
    "C_V2": {"n_segments": 4, "n_lesions": 2, "ablation": AblationConfig()},
    "D_oracle_continuous": {"n_segments": 4, "n_lesions": 2, "ablation": AblationConfig()},
    # Ablation arms (only meaningful for C_V2 base)
    "V2_no_rate_limit": {"n_segments": 4, "n_lesions": 2, "ablation": AblationConfig(enable_rate_limit=False)},
    "V2_no_hysteresis": {"n_segments": 4, "n_lesions": 2, "ablation": AblationConfig(enable_hysteresis=False)},
    "V2_no_drainage_floor": {"n_segments": 4, "n_lesions": 2, "ablation": AblationConfig(enable_drainage_floor=False)},
    "V2_no_alpha_floor": {"n_segments": 4, "n_lesions": 2, "ablation": AblationConfig(enable_alpha_floor=False)},
}

ATTACK_MODES = [
    "none",
    "noise_3x",
    "sensor_dropout",
    "fast_occlusion",
    "slow_occlusion",
    "wrong_model",
    "multi_failure",
    "actuator_saturation",
    "controller_delay",
]

def make_cfg(scenario: str, seed: int, attack: str) -> SimConfigV2Full:
    arm = ARMS[scenario]
    return SimConfigV2Full(
        scenario=scenario, seed=seed, attack_mode=attack,
        n_segments=arm["n_segments"], n_lesions=arm["n_lesions"],
        ablation=arm["ablation"]
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="P-01 V2 Full Robustness + Ablation Matrix")
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--arms", default="core", help="core (A/B/C/D) or all (8 arms) or comma-separated")
    ap.add_argument("--attacks", default="all", help="comma-separated or all")
    ap.add_argument("--output", default="p01_V2_full_validation_results.json")
    args = ap.parse_args()

    if args.arms == "core":
        arms = ["A_simple", "B_predictive_closed_loop", "C_V2", "D_oracle_continuous"]
    elif args.arms == "all":
        arms = list(ARMS.keys())
    else:
        arms = args.arms.split(",")

    attacks = ATTACK_MODES if args.attacks == "all" else args.attacks.split(",")

    here = os.path.dirname(os.path.abspath(__file__))
    all_results = []

    total_runs = len(arms) * len(attacks) * len(args.seeds)
    print(f"Running {total_runs} simulations: {len(arms)} arms × {len(attacks)} attacks × {len(args.seeds)} seeds")
    print()

    run_count = 0
    for attack in attacks:
        print(f"=== ATTACK: {attack} ===")
        for arm in arms:
            for seed in args.seeds:
                cfg = make_cfg(arm, seed, attack)
                r = run_v2_full(cfg)
                all_results.append(asdict(r))
                run_count += 1
                if run_count % 20 == 0:
                    print(f"  [{run_count}/{total_runs}] {arm} seed={seed} {attack}: t_fail={r.metric_3_time_to_critical_failure_hr}h peak={r.metric_1_peak_icp_mmhg}")

        # Print summary per attack
        for arm in arms:
            arm_runs = [r for r in all_results if r["scenario"] == arm and r["attack_mode"] == attack]
            if arm_runs:
                avg_tfail = sum(r["metric_3_time_to_critical_failure_hr"] for r in arm_runs) / len(arm_runs)
                avg_peak = sum(r["metric_1_peak_icp_mmhg"] for r in arm_runs) / len(arm_runs)
                print(f"  {arm:30s}: t_fail={avg_tfail:6.2f}h  peak={avg_peak:7.1f}mmHg")
        print()

    # Save results
    out = os.path.join(here, args.output)
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Wrote {len(all_results)} runs to {out}")

    # Print decisive comparison: V2 vs B
    print()
    print("=" * 100)
    print("DECISIVE COMPARISON: V2 vs B (existing predictive closed-loop)")
    print("=" * 100)
    print(f"{'Attack':<22} {'B t_fail':<10} {'V2 t_fail':<10} {'V2/B':<8} {'B peak':<10} {'V2 peak':<10} {'B false':<8} {'V2 false':<8} {'Verdict':<15}")
    print("-" * 100)

    v2_wins = 0
    for attack in attacks:
        b_runs = [r for r in all_results if r["scenario"] == "B_predictive_closed_loop" and r["attack_mode"] == attack]
        v2_runs = [r for r in all_results if r["scenario"] == "C_V2" and r["attack_mode"] == attack]
        if not b_runs or not v2_runs:
            continue
        b_tfail = sum(r["metric_3_time_to_critical_failure_hr"] for r in b_runs) / len(b_runs)
        v2_tfail = sum(r["metric_3_time_to_critical_failure_hr"] for r in v2_runs) / len(v2_runs)
        b_peak = sum(r["metric_1_peak_icp_mmhg"] for r in b_runs) / len(b_runs)
        v2_peak = sum(r["metric_1_peak_icp_mmhg"] for r in v2_runs) / len(v2_runs)
        b_false = sum(r["metric_5_false_interventions"] for r in b_runs) / len(b_runs)
        v2_false = sum(r["metric_5_false_interventions"] for r in v2_runs) / len(v2_runs)
        ratio = v2_tfail / max(b_tfail, 0.01)
        v2_better = (v2_tfail > b_tfail * 1.10) and (v2_peak <= b_peak * 1.1)
        if v2_better:
            verdict = "V2 BETTER"
            v2_wins += 1
        elif v2_tfail > b_tfail:
            verdict = "V2 marginal"
        else:
            verdict = "V2 WORSE"
        print(f"{attack:<22} {b_tfail:<10.2f} {v2_tfail:<10.2f} {ratio:<8.2f} {b_peak:<10.1f} {v2_peak:<10.1f} {b_false:<8.1f} {v2_false:<8.1f} {verdict:<15}")

    print()
    print(f"V2 materially outperforms B on {v2_wins}/{len(attacks)} attack modes.")

    # Ablation summary
    if "V2_no_rate_limit" in arms:
        print()
        print("=" * 100)
        print("ABLATION: Which V2 mechanism creates the improvement?")
        print("=" * 100)
        print(f"{'Attack':<22} {'V2 full':<12} {'no_rate':<12} {'no_hyst':<12} {'no_drain':<12} {'no_alpha':<12}")
        print("-" * 100)
        for attack in attacks:
            v2_runs = [r for r in all_results if r["scenario"] == "C_V2" and r["attack_mode"] == attack]
            nr_runs = [r for r in all_results if r["scenario"] == "V2_no_rate_limit" and r["attack_mode"] == attack]
            nh_runs = [r for r in all_results if r["scenario"] == "V2_no_hysteresis" and r["attack_mode"] == attack]
            nd_runs = [r for r in all_results if r["scenario"] == "V2_no_drainage_floor" and r["attack_mode"] == attack]
            na_runs = [r for r in all_results if r["scenario"] == "V2_no_alpha_floor" and r["attack_mode"] == attack]
            def avg_tfail(runs):
                return sum(r["metric_3_time_to_critical_failure_hr"] for r in runs) / len(runs) if runs else 0
            print(f"{attack:<22} {avg_tfail(v2_runs):<12.2f} {avg_tfail(nr_runs):<12.2f} {avg_tfail(nh_runs):<12.2f} {avg_tfail(nd_runs):<12.2f} {avg_tfail(na_runs):<12.2f}")


if __name__ == "__main__":
    main()

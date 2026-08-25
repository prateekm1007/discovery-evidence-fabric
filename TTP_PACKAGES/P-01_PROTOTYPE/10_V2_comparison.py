"""
P-01 V2 — Risk-Limited Continuous Conductance Controller
========================================================

R280 directive: "The potentially valuable mechanism is the rate-limited
hydraulic reallocation under uncertainty, not generic closed-loop control."

V2 extracts the R279 failure lesson as a design constraint:
  - Hard isolation (V1.0/V1.1 Arm C) is FRAGILE under sensor noise
  - Soft modulation (V1.2 Arm D) is robust but has no rate limiting
  - V2 = D + rate limiting + drainage floor + hysteresis

V2 MECHANISM (genuinely different from D):
  1. Estimate per-segment degradation (same trend predictor)
  2. Compute desired alpha per segment based on risk (high-risk → lower alpha)
  3. RATE-LIMIT the alpha change: |alpha_new - alpha_old| <= MAX_ALPHA_RATE * dt
     This prevents abrupt hydraulic transients even if predictor jumps.
  4. PRESERVE minimum drainage: sum(alpha_i * G_i * P_ICP) >= DRAINAGE_FLOOR
     If risk-based allocation would violate this, override toward more drainage.
  5. NO HARD ISOLATION: alpha floor at ALPHA_MIN (e.g., 0.05). Segments
     never fully close. No discrete "isolation" events.
  6. HYSTERESIS: alpha only changes if the desired change exceeds a deadband.
     Reduces valve actuation frequency (addresses R278 energy concern).

HYPOTHESIS: V2's rate limiting makes it robust to sensor noise (false
positive predictions don't cause sudden conductance drops), and the
drainage floor prevents collapse from over-cautious allocation.

DECISIVE QUESTION: Does V2 materially outperform B (existing predictive
closed-loop) under realistic uncertainty?

If NO → close P-01.
If YES → worth a physical bench test.

Constitutional basis:
- Article XXX: simulator NOT tuned to make V2 win. Same physics, same
  occlusion model, same sensor noise as A/B/D.
- Article XXVIII: V2 must earn its own promotion. It is NOT D rebranded.
- Article XXXI: V1.0/V1.1/V1.2 preserved in git history.

Arms:
  A = simple valve (1 segment, fixed, no control)
  B = existing predictive closed-loop modulation (V1.2 Arm D, no rate limiting)
  C = P-01 V2 continuous risk-limited modulation (NEW)
  D = oracle optimal continuous controller (perfect knowledge, rate-limited)

Attack modes:
  1. noise_1x (baseline)
  2. noise_2x
  3. noise_3x
  4. fast_occlusion (k_occl = 5x default)
  5. slow_occlusion (k_occl = 0.2x default)
  6. sensor_dropout (sensor goes to 0 for 60s every ~10 min)
  7. actuator_saturation (alpha capped at 0.7 instead of 1.0)
  8. wrong_model (controller assumes linear decay, actual is exponential)
  9. multi_failure (4 lesions instead of 2)

Run:
    python 10_V2_comparison.py
    python 10_V2_comparison.py --attacks all
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

# Import V1.2 for physics constants and helpers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_v12 = __import__("08_ABCDE_comparison")

P_MIN_MMHG = _v12.P_MIN_MMHG
P_MAX_MMHG = _v12.P_MAX_MMHG
P_TARGET_MMHG = _v12.P_TARGET_MMHG
F_MAX_PER_SEG = _v12.F_MAX_PER_SEG
Q_PRODUCTION_ML_MIN = _v12.Q_PRODUCTION_ML_MIN
G_HEALTHY = _v12.G_HEALTHY
DT_SEC = _v12.DT_SEC
N_STEPS = _v12.N_STEPS
SENSOR_NOISE_P_SIGMA = _v12.SENSOR_NOISE_P_SIGMA
SENSOR_NOISE_F_SIGMA = _v12.SENSOR_NOISE_F_SIGMA
K_OCCL_DEFAULT = _v12.K_OCCL_DEFAULT

SegmentState = _v12.SegmentState
estimate_occlusion_probability = _v12.estimate_occlusion_probability
true_conductance = _v12.true_conductance
SimResultV11 = _v12.SimResultV11


# ---------------------------------------------------------------------------
# V2 constants (the NEW mechanism parameters)
# ---------------------------------------------------------------------------

# Rate limiting: alpha can change by at most this fraction per second
# At 1 Hz loop rate, this means max 2% change per step.
# Tuned to allow response to real lesions (which develop over ~1 hour)
# but prevent response to sensor noise spikes (which are sub-second).
MAX_ALPHA_RATE_PER_SEC = 0.02   # = 2% per second = 72% per minute

# Alpha floor: segments never close below this. Prevents hard isolation.
ALPHA_MIN = 0.05                # 5% minimum opening

# Drainage floor: total drainage must stay above this fraction of target
DRAINAGE_FLOOR_FRACTION = 0.50  # never let total drainage drop below 50% of Q_production

# Hysteresis deadband: alpha only changes if desired change exceeds this
HYSTERESIS_DEADBAND = 0.03       # 3% deadband


# ---------------------------------------------------------------------------
# V2 Controller: risk-limited continuous conductance with rate limiting
# ---------------------------------------------------------------------------

def v2_controller(segs: List[SegmentState],
                  p_obs: float,
                  F_obs: List[float],
                  cfg: 'SimConfigV2',
                  t_sec: float) -> Tuple[List[float], int]:
    """
    P-01 V2: Risk-Limited Continuous Conductance Controller.

    Mechanism (4 layers, each addressing a R279 failure mode):

    Layer 1 — RISK ESTIMATION
      Same trend predictor as V1.x. Estimates P(occlusion) per segment
      from observed conductance trend.

    Layer 2 — RISK-AWARE ALLOCATION
      Desired alpha_i = ALPHA_MIN + (1 - ALPHA_MIN) * (1 - risk_i)^2 * normalize
      High-risk segments get lower alpha (but never below ALPHA_MIN).
      Low-risk segments get higher alpha.
      This is similar to V1.2 Arm D, but with explicit ALPHA_MIN floor.

    Layer 3 — DRAINAGE FLOOR PROTECTION
      If sum(alpha_i * G_HEALTHY * p_obs) < DRAINAGE_FLOOR, override
      allocation: scale all alphas up uniformly until floor is met
      (capped at INV-2 limit). This prevents collapse from over-cautious
      risk allocation.

    Layer 4 — RATE LIMITING + HYSTERESIS
      |alpha_new - alpha_old| <= MAX_ALPHA_RATE * dt
      Only update alpha if |desired - current| > HYSTERESIS_DEADBAND
      This prevents abrupt hydraulic transients from sensor noise spikes
      or predictor false positives.

    The combination of layers 3 + 4 is what makes V2 different from D:
    D has no drainage floor (can collapse if all segments look risky)
    D has no rate limiting (can spike ICP if predictor jumps)
    """
    n = len(segs)
    interventions = 0

    # Layer 1: Risk estimation
    p_occl = [estimate_occlusion_probability(s, 0.0) for s in segs]

    # Layer 2: Risk-aware allocation
    # Desired alpha per segment: high risk → low alpha, low risk → high alpha
    # Using (1 - risk)^2 weighting like V1.2 Arm D, but with ALPHA_MIN floor
    weights = [(1.0 - p_occl[i]) ** 2 for i in range(n)]
    total_weight = sum(weights)

    # PI controller on total conductance (same as V1.x)
    K_p = 0.020
    g_total_target = (Q_PRODUCTION_ML_MIN / P_TARGET_MMHG) + K_p * (p_obs - P_TARGET_MMHG)
    g_total_min = Q_PRODUCTION_ML_MIN / P_MAX_MMHG
    g_total_max = Q_PRODUCTION_ML_MIN / P_MIN_MMHG
    g_total_target = max(g_total_min, min(g_total_max, g_total_target))

    # INV-2 cap
    if p_obs > 0.1:
        alpha_inv2_cap = F_MAX_PER_SEG / (G_HEALTHY * p_obs)
    else:
        alpha_inv2_cap = 1.0
    alpha_inv2_cap = max(0.0, min(1.0, alpha_inv2_cap))

    # Compute desired alpha per segment
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

    # Layer 3: Drainage floor protection
    # If total drainage would be below floor, scale up uniformly
    current_total_G = sum(alpha_desired[i] * G_HEALTHY for i in range(n))
    drainage_predicted = current_total_G * max(p_obs, 0.1)
    drainage_floor = Q_PRODUCTION_ML_MIN * DRAINAGE_FLOOR_FRACTION

    if drainage_predicted < drainage_floor and current_total_G > 1e-9:
        # Need to scale up. Target drainage = drainage_floor
        # G_total_needed = drainage_floor / p_obs
        scale_factor = (drainage_floor / max(p_obs, 0.1)) / current_total_G
        scale_factor = min(scale_factor, alpha_inv2_cap / max(alpha_desired[0], 0.01))  # don't exceed INV-2 cap
        for i in range(n):
            alpha_desired[i] = min(alpha_inv2_cap, alpha_desired[i] * scale_factor)

    # Layer 4: Rate limiting + hysteresis
    alpha_cmd = [0.0] * n
    for i, s in enumerate(segs):
        desired = alpha_desired[i]
        current = s.alpha

        # Hysteresis: only change if difference exceeds deadband
        if abs(desired - current) < HYSTERESIS_DEADBAND:
            alpha_cmd[i] = current  # no change
        else:
            # Rate limit: max change per step
            max_change = MAX_ALPHA_RATE_PER_SEC * DT_SEC
            delta = desired - current
            delta = max(-max_change, min(max_change, delta))
            alpha_cmd[i] = current + delta

        # Apply actuator saturation if attack mode
        if cfg.attack_mode == "actuator_saturation":
            alpha_cmd[i] = min(alpha_cmd[i], 0.70)

    return alpha_cmd, interventions


# ---------------------------------------------------------------------------
# Oracle continuous controller (Arm D in V2 framework)
# ---------------------------------------------------------------------------

def oracle_continuous_controller(segs: List[SegmentState],
                                 p_obs: float,
                                 F_obs: List[float],
                                 cfg: 'SimConfigV2',
                                 t_sec: float) -> Tuple[List[float], int]:
    """
    Oracle: perfect knowledge of lesion states, but still continuous (no isolation).
    Uses TRUE conductance (not observed) to compute optimal allocation.
    Rate-limited like V2 for fair comparison.

    This establishes the upper bound for continuous control with perfect information.
    """
    n = len(segs)
    interventions = 0

    # Oracle knows TRUE conductance of each segment
    true_G = [true_conductance(s, t_sec, cfg.k_occl) for s in segs]
    total_true_G = sum(true_G)

    # PI controller on total conductance
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

    # Oracle allocation: distribute alpha proportional to TRUE remaining conductance
    # Healthy segments (high true_G) get more alpha; failing segments (low true_G) get less
    # This is optimal because it maximizes usable conductance
    if total_true_G > 1e-9:
        alpha_desired = []
        for i in range(n):
            # Target: alpha_i * G_HEALTHY = share of g_total_target proportional to true_G_i
            share = true_G[i] / total_true_G
            alpha_desired_i = share * g_total_target / G_HEALTHY
            alpha_desired_i = max(ALPHA_MIN, min(alpha_inv2_cap, alpha_desired_i))
            alpha_desired.append(alpha_desired_i)
    else:
        alpha_desired = [ALPHA_MIN] * n

    # Rate limit (same as V2 for fair comparison)
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

    return alpha_cmd, interventions


# ---------------------------------------------------------------------------
# V2 Config
# ---------------------------------------------------------------------------

@dataclass
class SimConfigV2:
    n_segments: int = 4
    seed: int = 42
    scenario: str = "C_V2"  # A_simple | B_predictive_closed_loop | C_V2 | D_oracle_continuous
    k_occl: float = K_OCCL_DEFAULT
    lesion_onset_window_hr: tuple = (2.0, 18.0)
    n_lesions: int = 2
    sensor_noise: bool = True
    actuator_delay: bool = True
    attack_mode: str = "none"
    sensor_noise_multiplier: float = 1.0
    # For wrong_model attack: actual occlusion is linear, controller expects exponential
    wrong_model: bool = False


# ---------------------------------------------------------------------------
# V2 simulation loop
# ---------------------------------------------------------------------------

def true_conductance_v2(seg: SegmentState, t_sec: float, k_occl: float, wrong_model: bool = False) -> float:
    """Extended conductance function. If wrong_model, actual decay is LINEAR (not exponential)."""
    if seg.isolated:
        return 0.0
    base = seg.alpha_delayed * G_HEALTHY
    if t_sec < seg.lesion_start_sec:
        return base
    elapsed = t_sec - seg.lesion_start_sec
    if wrong_model:
        # Linear decay: G = base * max(0, 1 - k_occl * elapsed)
        decay = max(0.0, 1.0 - k_occl * elapsed * 0.3)  # *0.3 to match timescale roughly
    else:
        # Exponential decay (default)
        decay = math.exp(-k_occl * elapsed)
    return base * decay


def run_v2(cfg: SimConfigV2) -> SimResultV11:
    random.seed(cfg.seed)

    # Apply attack modes
    if cfg.attack_mode in ("noise_2x",):
        cfg.sensor_noise_multiplier = 2.0
    elif cfg.attack_mode in ("noise_3x",):
        cfg.sensor_noise_multiplier = 3.0
    elif cfg.attack_mode == "fast_occlusion":
        cfg.k_occl = 5.0 * K_OCCL_DEFAULT
    elif cfg.attack_mode == "slow_occlusion":
        cfg.k_occl = 0.2 * K_OCCL_DEFAULT
    elif cfg.attack_mode == "wrong_model":
        cfg.wrong_model = True
    elif cfg.attack_mode == "multi_failure":
        # All segments fail — but cap at n_segments (1-segment A_simple can only have 1 lesion)
        cfg.n_lesions = cfg.n_segments

    noise_p = SENSOR_NOISE_P_SIGMA * cfg.sensor_noise_multiplier
    noise_f = SENSOR_NOISE_F_SIGMA * cfg.sensor_noise_multiplier

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
    time_above_20_sec = 0.0
    drainage_achieved_ml = 0.0
    drainage_target_ml = Q_PRODUCTION_ML_MIN * (N_STEPS * DT_SEC / 60.0)
    time_to_critical_failure_sec = N_STEPS * DT_SEC
    intervention_count_total = 0
    alpha_change_count = 0
    prev_alpha = [s.alpha for s in segs]

    icp_violation_total = 0.0
    overload_events = 0
    in_overload = [False] * cfg.n_segments
    in_icp_violation = False

    prediction_lead_times: List[float] = []
    survival = True
    notes: List[str] = []

    # Sensor dropout state
    dropout_active = False
    dropout_timer = 0
    dropout_next = random.uniform(300, 900)  # next dropout in 5-15 min

    for step in range(N_STEPS):
        t_sec = step * DT_SEC

        for s in segs:
            s.alpha_delayed = s.alpha

        # Plant step
        G = [true_conductance_v2(s, t_sec, cfg.k_occl, cfg.wrong_model) for s in segs]
        G_sum = sum(G)
        if G_sum <= 1e-9:
            p_true = 10.0 * P_MAX_MMHG
        else:
            p_true = Q_PRODUCTION_ML_MIN / G_sum
        F_true = [g * p_true for g in G]

        # Sensor with dropout attack
        if cfg.attack_mode == "sensor_dropout":
            if dropout_active:
                p_obs = 0.0  # sensor reads 0
                F_obs = [0.0] * cfg.n_segments
                dropout_timer -= DT_SEC
                if dropout_timer <= 0:
                    dropout_active = False
                    dropout_next = random.uniform(300, 900)
            else:
                dropout_next -= DT_SEC
                if dropout_next <= 0:
                    dropout_active = True
                    dropout_timer = 60.0  # 60-second dropout
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
                g_obs_i = max(0.0, F_obs[i] / p_obs)
            else:
                g_obs_i = 0.0
            s.history_G.append(g_obs_i)

        # Controller dispatch
        if cfg.scenario == "C_V2":
            alpha_cmd, interventions_this_step = v2_controller(segs, p_obs, F_obs, cfg, t_sec)
        elif cfg.scenario == "D_oracle_continuous":
            alpha_cmd, interventions_this_step = oracle_continuous_controller(segs, p_obs, F_obs, cfg, t_sec)
        elif cfg.scenario == "B_predictive_closed_loop":
            # V1.2 Arm D logic (no rate limiting, no drainage floor)
            v12_cfg = _v12.SimConfigV12(
                n_segments=cfg.n_segments, seed=cfg.seed,
                scenario="D_predictive_closed_loop",
                k_occl=cfg.k_occl, lesion_onset_window_hr=cfg.lesion_onset_window_hr,
                n_lesions=cfg.n_lesions, sensor_noise=cfg.sensor_noise,
                actuator_delay=cfg.actuator_delay, isolation_mode="none",
                attack_mode="none")
            alpha_cmd, interventions_this_step = _v12.arm_d_allocator(segs, p_obs, F_obs, v12_cfg)
        else:  # A_simple
            alpha_cmd = [1.0] * cfg.n_segments  # fixed open
            interventions_this_step = 0

        intervention_count_total += interventions_this_step

        for i, s in enumerate(segs):
            if not s.isolated:
                s.alpha = alpha_cmd[i]
            else:
                s.alpha = 0.0
            if abs(s.alpha - prev_alpha[i]) > 0.005:  # lowered threshold for V2's slow changes
                alpha_change_count += 1
            prev_alpha[i] = s.alpha

        for s in segs:
            if s.isolated and s.isolation_time_sec is None:
                s.isolation_time_sec = t_sec
                if s.occlusion_active:
                    catastrophic_time = s.lesion_start_sec + (math.log(0.1) / -cfg.k_occl)
                    lead = catastrophic_time - t_sec
                    if lead > 0:
                        prediction_lead_times.append(lead)

        # Metrics
        icp_max = max(icp_max, p_true)
        icp_min = min(icp_min, p_true)

        if p_true > P_MAX_MMHG:
            time_above_20_sec += DT_SEC

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

    drainage_pct = (drainage_achieved_ml / drainage_target_ml * 100.0) if drainage_target_ml > 0 else 0.0
    t_fail_hr = time_to_critical_failure_sec / 3600.0
    energy_per_hr = alpha_change_count / (N_STEPS * DT_SEC / 3600.0) if N_STEPS > 0 else 0.0
    lead_avg = (sum(prediction_lead_times) / len(prediction_lead_times)
                if prediction_lead_times else None)

    return SimResultV11(
        scenario=cfg.scenario,
        seed=cfg.seed,
        metric_1_peak_icp_mmhg=round(icp_max if icp_max != float("-inf") else 0.0, 2),
        metric_2_time_above_20_mmhg_sec=round(time_above_20_sec, 1),
        metric_3_drainage_capacity_percent=round(drainage_pct, 1),
        metric_4_time_to_critical_failure_hr=round(t_fail_hr, 2),
        metric_5_intervention_count=intervention_count_total,
        metric_6_controller_energy_changes_per_hr=round(energy_per_hr, 1),
        invariant_1_held=(icp_violation_total == 0),
        invariant_2_held=(overload_events == 0),
        survival=survival,
        icp_min=round(icp_min if icp_min != float("inf") else 0.0, 2),
        icp_max=round(icp_max if icp_max != float("-inf") else 0.0, 2),
        isolation_count=sum(1 for s in segs if s.isolated),
        prediction_lead_time_sec_avg=round(lead_avg, 1) if lead_avg else None,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Scenario presets
# ---------------------------------------------------------------------------

def make_cfg_v2(scenario: str, seed: int, attack: str = "none") -> SimConfigV2:
    if scenario == "A_simple":
        return SimConfigV2(scenario="A_simple", seed=seed,
                           n_segments=1, n_lesions=1, attack_mode=attack)
    elif scenario == "B_predictive_closed_loop":
        return SimConfigV2(scenario="B_predictive_closed_loop", seed=seed,
                           n_segments=4, n_lesions=2, attack_mode=attack)
    elif scenario == "C_V2":
        return SimConfigV2(scenario="C_V2", seed=seed,
                           n_segments=4, n_lesions=2, attack_mode=attack)
    elif scenario == "D_oracle_continuous":
        return SimConfigV2(scenario="D_oracle_continuous", seed=seed,
                           n_segments=4, n_lesions=2, attack_mode=attack)
    else:
        raise ValueError(f"Unknown scenario: {scenario}")


ATTACK_MODES = [
    "none",           # baseline (1x noise, default occlusion)
    "noise_2x",
    "noise_3x",
    "fast_occlusion",
    "slow_occlusion",
    "sensor_dropout",
    "actuator_saturation",
    "wrong_model",
    "multi_failure",
]

SCENARIOS = ["A_simple", "B_predictive_closed_loop", "C_V2", "D_oracle_continuous"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="P-01 V2 Comparison")
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--attacks", default="all",
                    help="Comma-separated list of attacks, or 'all'")
    args = ap.parse_args()

    attacks = ATTACK_MODES if args.attacks == "all" else args.attacks.split(",")

    here = os.path.dirname(os.path.abspath(__file__))

    all_results = []
    print("=" * 120)
    print("P-01 V2 — RISK-LIMITED CONTINUOUS CONDUCTANCE CONTROLLER")
    print("Decisive question: Does V2 materially outperform B (existing predictive closed-loop) under realistic uncertainty?")
    print("=" * 120)
    print()

    # Run all scenarios × all attacks × all seeds
    for attack in attacks:
        print(f"=== ATTACK: {attack} ===")
        for sc in SCENARIOS:
            for sd in args.seeds:
                cfg = make_cfg_v2(sc, sd, attack)
                r = run_v2(cfg)
                r_dict = asdict(r)
                r_dict["attack_mode"] = attack
                all_results.append(r_dict)
            # Print summary for this scenario
            sc_runs = [r for r in all_results if r["scenario"] == sc and r["attack_mode"] == attack]
            avg_tfail = sum(r["metric_4_time_to_critical_failure_hr"] for r in sc_runs) / len(sc_runs)
            avg_peak = sum(r["metric_1_peak_icp_mmhg"] for r in sc_runs) / len(sc_runs)
            print(f"  {sc:30s}: avg_tfail={avg_tfail:6.2f}h  avg_peak={avg_peak:6.1f}mmHg")
        print()

    # Summary table: V2 vs B across all attacks
    print("=" * 120)
    print("V2 vs B SUMMARY (does V2 materially outperform B under uncertainty?)")
    print("=" * 120)
    print(f"{'Attack':<22} {'B t_fail (h)':<14} {'V2 t_fail (h)':<14} {'V2/B ratio':<12} {'B peak':<10} {'V2 peak':<10} {'Verdict':<20}")
    print("-" * 120)

    v2_beats_b_count = 0
    total_attacks = 0

    for attack in attacks:
        b_runs = [r for r in all_results if r["scenario"] == "B_predictive_closed_loop" and r["attack_mode"] == attack]
        v2_runs = [r for r in all_results if r["scenario"] == "C_V2" and r["attack_mode"] == attack]

        if not b_runs or not v2_runs:
            continue

        b_tfail = sum(r["metric_4_time_to_critical_failure_hr"] for r in b_runs) / len(b_runs)
        v2_tfail = sum(r["metric_4_time_to_critical_failure_hr"] for r in v2_runs) / len(v2_runs)
        b_peak = sum(r["metric_1_peak_icp_mmhg"] for r in b_runs) / len(b_runs)
        v2_peak = sum(r["metric_1_peak_icp_mmhg"] for r in v2_runs) / len(v2_runs)

        ratio = v2_tfail / max(b_tfail, 0.01)
        v2_better = (v2_tfail > b_tfail * 1.10) and (v2_peak <= b_peak)  # 10% better + not worse on peak

        if v2_better:
            verdict = "V2 BETTER"
            v2_beats_b_count += 1
        elif v2_tfail > b_tfail:
            verdict = "V2 marginally better"
        elif v2_tfail < b_tfail * 0.9:
            verdict = "V2 WORSE"
        else:
            verdict = "V2 ≈ B"

        total_attacks += 1
        print(f"{attack:<22} {b_tfail:<14.2f} {v2_tfail:<14.2f} {ratio:<12.2f} {b_peak:<10.1f} {v2_peak:<10.1f} {verdict:<20}")

    print()
    print("=" * 120)
    print("DECISIVE VERDICT")
    print("=" * 120)
    print(f"V2 materially outperforms B on {v2_beats_b_count}/{total_attacks} attack modes.")

    if v2_beats_b_count >= 6:  # majority of 9 attacks
        print("VERDICT: YES — V2 materially outperforms B under realistic uncertainty.")
        print("The rate-limited continuous conductance mechanism creates a genuine technical advantage.")
        print("P-01 V2 is worth a physical bench test.")
    elif v2_beats_b_count >= 3:
        print("VERDICT: PARTIAL — V2 outperforms B on some attacks but not consistently.")
        print("The mechanism has value in specific regimes but is not robustly superior.")
        print("Further design iteration needed before bench test.")
    else:
        print("VERDICT: NO — V2 does NOT materially outperform B under realistic uncertainty.")
        print("The rate-limited continuous conductance mechanism does NOT create a genuine technical advantage.")
        print("CLOSE P-01. The finding enters the cemetery as negative knowledge.")

    # Also show Oracle gap
    print()
    print("ORACLE GAP (how much of optimal continuous control does V2 capture?):")
    for attack in attacks:
        v2_runs = [r for r in all_results if r["scenario"] == "C_V2" and r["attack_mode"] == attack]
        d_runs = [r for r in all_results if r["scenario"] == "D_oracle_continuous" and r["attack_mode"] == attack]
        if v2_runs and d_runs:
            v2_tfail = sum(r["metric_4_time_to_critical_failure_hr"] for r in v2_runs) / len(v2_runs)
            d_tfail = sum(r["metric_4_time_to_critical_failure_hr"] for r in d_runs) / len(d_runs)
            pct = v2_tfail / max(d_tfail, 0.01) * 100
            print(f"  {attack:<22}: V2={v2_tfail:.2f}h vs Oracle={d_tfail:.2f}h → V2 captures {pct:.0f}% of oracle")

    print()
    print("HONEST DISCLOSURE (Article XXVIII):")
    print("  - This is a MODEL-VS-MODEL comparison, NOT clinical evidence.")
    print("  - V2 is NOT D rebranded. V2 adds: rate limiting, drainage floor, hysteresis, alpha floor.")
    print("  - If V2 does NOT beat B, we close P-01. No rebranding. No documentation around a failed mechanism.")
    print("  - Article XXX: simulator NOT tuned to make V2 win.")

    out = os.path.join(here, "p01_V2_comparison_results.json")
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nWrote {len(all_results)} runs to {out}")


if __name__ == "__main__":
    main()

"""
P-01 V1.2 — A/B/C/D/E Comparison with Strongest Baseline + Oracle
=================================================================

R279 directive: "Take one promising mechanism and force it to survive
increasingly realistic competition."

This file extends V1.1 (06_ABC_comparison.py) with two new arms:

  D = existing predictive closed-loop approach (strongest published baseline)
      Represents US20210338992A1 (closed-loop shunt with sensors + controller
      + valve + feedback) + 2023 ML study (ROC AUC 0.733 for shunt complication
      prediction). 4 segments, predictive risk model, closed-loop valve
      modulation — BUT NO ISOLATION, NO REDISTRIBUTION. The controller
      adjusts valve opening based on predicted risk but never fully closes
      a segment.

  E = Oracle (upper bound)
      Perfect knowledge of which segment will fail AND when. Isolates at
      the mathematically optimal moment (lesion onset). Establishes the
      theoretical maximum benefit of isolation+redistribution.

The central question becomes:
  1. Does C (predictive isolation) outperform D (predictive closed-loop
     without isolation)?  -> isolates the value of the ISOLATION mechanism
  2. How much of E's (oracle) benefit does C capture?  -> upper bound

R279 also corrects two overclaims from R278:
  - 59 mmHg is NOT "current standard of care" — it's the simulator's
    single-segment baseline. Clinical peak ICP data for shunt failure
    is not measured here.
  - The 7-9x result is NOT "clinical benefit" — it's a model-vs-model
    comparison. Clinical benefit requires bench + animal + human validation.

Constitutional basis:
- Article XXX: simulator NOT tuned to make C win. D and E use the SAME
  physics, SAME occlusion model, SAME sensor noise as A/B/C.
- Article XXVIII: the result determines the claim. If C does not beat D,
  P-01's value proposition is the ISOLATION mechanism, not prediction.
- Article XXXI: V1.0 (R277) and V1.1 (R278) preserved in git history.

Run:
    python 08_ABCDE_comparison.py
    python 08_ABCDE_comparison.py --seeds 42 43 44 45 46 47 48 49 50
    python 08_ABCDE_comparison.py --attack misspecification
    python 08_ABCDE_comparison.py --attack sensor-noise
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

# Import V1.1
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_v11 = __import__("06_ABC_comparison")

# Re-export
P_MIN_MMHG = _v11.P_MIN_MMHG
P_MAX_MMHG = _v11.P_MAX_MMHG
P_TARGET_MMHG = _v11.P_TARGET_MMHG
F_MAX_PER_SEG = _v11.F_MAX_PER_SEG
Q_PRODUCTION_ML_MIN = _v11.Q_PRODUCTION_ML_MIN
G_HEALTHY = _v11.G_HEALTHY
DT_SEC = _v11.DT_SEC
N_STEPS = _v11.N_STEPS
SENSOR_NOISE_P_SIGMA = _v11.SENSOR_NOISE_P_SIGMA
SENSOR_NOISE_F_SIGMA = _v11.SENSOR_NOISE_F_SIGMA
K_OCCL_DEFAULT = _v11.K_OCCL_DEFAULT

SegmentState = _v11.SegmentState
estimate_occlusion_probability = _v11.estimate_occlusion_probability
true_conductance = _v11.true_conductance
SimResultV11 = _v11.SimResultV11


# ---------------------------------------------------------------------------
# V1.2 config — adds D and E arms + attack modes
# ---------------------------------------------------------------------------

@dataclass
class SimConfigV12:
    n_segments: int = 4
    seed: int = 42
    scenario: str = "C_predictive"
    k_occl: float = K_OCCL_DEFAULT
    lesion_onset_window_hr: tuple = (2.0, 18.0)
    n_lesions: int = 2
    sensor_noise: bool = True
    actuator_delay: bool = True
    isolation_mode: str = "predictive"
    # V1.2 attack modes
    attack_mode: str = "none"  # none | misspecification | sensor-noise
    # Misspecification: controller assumes k_occl=0.5/hr but actual is 1.0/hr
    k_occl_controller_assumed: float = K_OCCL_DEFAULT  # controller's belief
    # Sensor-noise attack: 3x normal noise
    sensor_noise_multiplier: float = 1.0


# ---------------------------------------------------------------------------
# Arm D: Existing predictive closed-loop (NO isolation, NO redistribution)
# ---------------------------------------------------------------------------

def arm_d_allocator(segs: List[SegmentState],
                    p_obs: float,
                    F_obs: List[float],
                    cfg: SimConfigV12) -> Tuple[List[float], int]:
    """
    Arm D: Predictive closed-loop valve modulation WITHOUT isolation.

    Represents the strongest published approach:
    - US20210338992A1: closed-loop shunt with sensors + controller + valve
    - 2023 ML study: predictive risk model for shunt complications

    Strategy:
    - Same trend predictor as C (estimate_occlusion_probability)
    - BUT: never isolates (alpha never goes to 0)
    - Instead: modulates alpha based on risk — reduce flow on at-risk
      segments, increase on healthy ones
    - This is "soft redistribution" without hard isolation

    The point: does C's HARD ISOLATION add value beyond D's SOFT MODULATION?
    """
    n = len(segs)
    interventions = 0

    p_occl = [estimate_occlusion_probability(s, 0.0) for s in segs]

    # PI controller on total conductance (same as C)
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

    # KEY DIFFERENCE FROM C: distribute alpha INVERSELY to risk
    # Low-risk segments get MORE flow; high-risk segments get LESS flow
    # but NEVER zero (no isolation).
    # Weight: w_i = (1 - p_occl_i)^2  (squared to sharpen the contrast)
    # Minimum alpha floor: 0.05 (5% — never fully close)
    ALPHA_FLOOR = 0.05

    weights = [(1.0 - p_occl[i]) ** 2 for i in range(n)]
    total_weight = sum(weights)

    alpha_cmd = [0.0] * n
    if total_weight > 1e-9:
        for i in range(n):
            share = weights[i] / total_weight
            alpha_cmd[i] = max(ALPHA_FLOOR, min(alpha_inv2_cap,
                                                share * g_total_target / G_HEALTHY))
    else:
        # All segments equally risky — distribute equally
        alpha_per = g_total_target / (G_HEALTHY * n)
        for i in range(n):
            alpha_cmd[i] = max(ALPHA_FLOOR, min(alpha_inv2_cap, alpha_per))

    return alpha_cmd, interventions


# ---------------------------------------------------------------------------
# Arm E: Oracle (perfect knowledge, optimal isolation timing)
# ---------------------------------------------------------------------------

def arm_e_allocator(segs: List[SegmentState],
                    p_obs: float,
                    F_obs: List[float],
                    cfg: SimConfigV12,
                    t_sec: float) -> Tuple[List[float], int]:
    """
    Arm E: Oracle. Perfect knowledge of which segment will fail AND when.

    Isolates at the mathematically optimal moment: the instant a lesion
    begins (lesion_start_sec). This is the earliest possible detection —
    no real controller could achieve this without future knowledge.

    Establishes the UPPER BOUND: how much benefit is theoretically
    available from isolation+redistribution?

    Among non-isolated segments, uses the same PI controller as C.
    """
    n = len(segs)
    interventions = 0

    # Oracle isolation: isolate the moment a lesion begins
    for i, s in enumerate(segs):
        if s.isolated:
            continue
        if s.occlusion_active and t_sec >= s.lesion_start_sec:
            s.isolated = True
            s.isolation_time_sec = t_sec
            interventions += 1

    # Among survivors, same PI controller as C
    survivors = [i for i, s in enumerate(segs) if not s.isolated]
    if not survivors:
        return [0.0] * n, interventions

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

    alpha_per_survivor = max(0.0, min(alpha_inv2_cap,
                                       g_total_target / (G_HEALTHY * len(survivors))))

    alpha_cmd = [0.0] * n
    for i in survivors:
        alpha_cmd[i] = alpha_per_survivor

    return alpha_cmd, interventions


# ---------------------------------------------------------------------------
# V1.2 simulation loop (extends V1.1 to support D and E)
# ---------------------------------------------------------------------------

def run_v12(cfg: SimConfigV12) -> SimResultV11:
    random.seed(cfg.seed)

    # Apply attack modes
    # Misspecification: actual occlusion is 2x faster than the default the
    # controller was tuned for. The controller's predictor threshold
    # (ISOLATE_THRESHOLD=0.4, PREDICTOR_WINDOW=1800s) was calibrated for
    # k_occl=1.0/hr. With k_occl=2.0/hr, the lesion progresses faster than
    # the predictor expects, so it may fire too late.
    if cfg.attack_mode == "misspecification":
        cfg.k_occl = 2.0 * K_OCCL_DEFAULT  # actual occlusion 2x faster
    # Sensor-noise attack: 3x normal noise
    if cfg.attack_mode == "sensor-noise":
        cfg.sensor_noise_multiplier = 3.0

    noise_p = SENSOR_NOISE_P_SIGMA * cfg.sensor_noise_multiplier
    noise_f = SENSOR_NOISE_F_SIGMA * cfg.sensor_noise_multiplier

    segs = [SegmentState(idx=i, n_segments_total=cfg.n_segments) for i in range(cfg.n_segments)]

    lesion_times = sorted(random.uniform(cfg.lesion_onset_window_hr[0],
                                         cfg.lesion_onset_window_hr[1])
                          for _ in range(cfg.n_lesions))
    for t_hr, seg_idx in zip(lesion_times, range(cfg.n_lesions)):
        segs[seg_idx].lesion_start_sec = t_hr * 3600.0
        segs[seg_idx].occlusion_active = True

    # Trackers (same 6 metrics as V1.1)
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

    for step in range(N_STEPS):
        t_sec = step * DT_SEC

        for s in segs:
            s.alpha_delayed = s.alpha

        # Plant step (uses ACTUAL k_occl, not controller's assumed)
        G = [true_conductance(s, t_sec, cfg.k_occl) for s in segs]
        G_sum = sum(G)
        if G_sum <= 1e-9:
            p_true = 10.0 * P_MAX_MMHG
        else:
            p_true = Q_PRODUCTION_ML_MIN / G_sum
        F_true = [g * p_true for g in G]

        # Sensor
        if cfg.sensor_noise:
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

        # Controller dispatch by arm
        if cfg.scenario == "D_predictive_closed_loop":
            alpha_cmd, interventions_this_step = arm_d_allocator(segs, p_obs, F_obs, cfg)
        elif cfg.scenario == "E_oracle":
            alpha_cmd, interventions_this_step = arm_e_allocator(segs, p_obs, F_obs, cfg, t_sec)
        else:
            # A/B/C use V1.1 allocator
            v11_cfg = _v11.SimConfigV11(
                n_segments=cfg.n_segments, seed=cfg.seed, scenario=cfg.scenario,
                k_occl=cfg.k_occl, lesion_onset_window_hr=cfg.lesion_onset_window_hr,
                n_lesions=cfg.n_lesions, sensor_noise=cfg.sensor_noise,
                actuator_delay=cfg.actuator_delay,
                isolation_mode=cfg.isolation_mode)
            alpha_cmd, interventions_this_step = _v11.v11_allocator(segs, p_obs, F_obs, v11_cfg)

        intervention_count_total += interventions_this_step

        for i, s in enumerate(segs):
            if not s.isolated:
                s.alpha = alpha_cmd[i]
            else:
                s.alpha = 0.0
            if abs(s.alpha - prev_alpha[i]) > 0.05:
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

        # 6-metric updates
        icp_max = max(icp_max, p_true)
        icp_min = min(icp_min, p_true)

        if p_true > P_MAX_MMHG:
            time_above_20_sec += DT_SEC

        actual_drainage_this_step = sum(F_true) * DT_SEC / 60.0
        drainage_achieved_ml += actual_drainage_this_step

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
            notes.append(f"t={t_sec/3600:.2f}h: ICP out of band >1hr cumulative")
            break

    drainage_capacity_pct = (drainage_achieved_ml / drainage_target_ml * 100.0) if drainage_target_ml > 0 else 0.0
    time_to_failure_hr = time_to_critical_failure_sec / 3600.0
    controller_energy_per_hr = alpha_change_count / (N_STEPS * DT_SEC / 3600.0) if N_STEPS > 0 else 0.0
    lead_avg = (sum(prediction_lead_times) / len(prediction_lead_times)
                if prediction_lead_times else None)

    return SimResultV11(
        scenario=cfg.scenario,
        seed=cfg.seed,
        metric_1_peak_icp_mmhg=round(icp_max if icp_max != float("-inf") else 0.0, 2),
        metric_2_time_above_20_mmhg_sec=round(time_above_20_sec, 1),
        metric_3_drainage_capacity_percent=round(drainage_capacity_pct, 1),
        metric_4_time_to_critical_failure_hr=round(time_to_failure_hr, 2),
        metric_5_intervention_count=intervention_count_total,
        metric_6_controller_energy_changes_per_hr=round(controller_energy_per_hr, 1),
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
# Scenario presets for V1.2
# ---------------------------------------------------------------------------

def make_cfg_v12(scenario: str, seed: int, attack: str = "none") -> SimConfigV12:
    if scenario == "A_conventional":
        return SimConfigV12(scenario="A_conventional", seed=seed,
                            n_segments=1, n_lesions=1, isolation_mode="none",
                            attack_mode=attack)
    elif scenario == "B_reactive":
        return SimConfigV12(scenario="B_reactive", seed=seed,
                            n_segments=4, n_lesions=2, isolation_mode="reactive",
                            attack_mode=attack)
    elif scenario == "C_predictive":
        return SimConfigV12(scenario="C_predictive", seed=seed,
                            n_segments=4, n_lesions=2, isolation_mode="predictive",
                            attack_mode=attack)
    elif scenario == "D_predictive_closed_loop":
        return SimConfigV12(scenario="D_predictive_closed_loop", seed=seed,
                            n_segments=4, n_lesions=2, isolation_mode="none",
                            attack_mode=attack)
    elif scenario == "E_oracle":
        return SimConfigV12(scenario="E_oracle", seed=seed,
                            n_segments=4, n_lesions=2, isolation_mode="none",
                            attack_mode=attack)
    else:
        raise ValueError(f"Unknown scenario: {scenario}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="P-01 V1.2 A/B/C/D/E Comparison")
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--attack", default="none",
                    choices=["none", "misspecification", "sensor-noise"],
                    help="Attack mode: none | misspecification (controller assumes wrong k_occl) | sensor-noise (3x noise)")
    ap.add_argument("--scenario", default=None,
                    choices=["A_conventional", "B_reactive", "C_predictive",
                             "D_predictive_closed_loop", "E_oracle"])
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    scenarios = (["A_conventional", "B_reactive", "C_predictive",
                  "D_predictive_closed_loop", "E_oracle"]
                 if args.scenario is None else [args.scenario])

    all_results = []
    print("=" * 110)
    print(f"P-01 V1.2 — A/B/C/D/E COMPARISON  (attack: {args.attack})")
    print("Central questions:")
    print("  1. Does C (predictive isolation) outperform D (predictive closed-loop WITHOUT isolation)?")
    print("     -> isolates the value of the ISOLATION mechanism")
    print("  2. How much of E's (oracle) benefit does C capture?")
    print("     -> upper bound on theoretically available benefit")
    print("=" * 110)
    print()

    for sc in scenarios:
        print(f"--- {sc} ---")
        for sd in args.seeds:
            cfg = make_cfg_v12(sc, sd, args.attack)
            r = run_v12(cfg)
            all_results.append(asdict(r))
            print(f"  seed={sd}: peak={r.metric_1_peak_icp_mmhg:6.1f}mmHg  "
                  f"t>20={r.metric_2_time_above_20_mmhg_sec:7.0f}s  "
                  f"drain={r.metric_3_drainage_capacity_percent:5.1f}%  "
                  f"t_fail={r.metric_4_time_to_critical_failure_hr:5.2f}h  "
                  f"interv={r.metric_5_intervention_count}  "
                  f"alpha/hr={r.metric_6_controller_energy_changes_per_hr:6.1f}  "
                  f"surv={'Y' if r.survival else 'N'}")
        print()

    # Comparison table
    print("=" * 110)
    print(f"A/B/C/D/E COMPARISON TABLE (mean across {len(args.seeds)} seeds, attack: {args.attack})")
    print("=" * 110)
    print(f"{'Metric':<35} {'A':<10} {'B':<10} {'C':<10} {'D':<10} {'E':<10} {'C vs D':<12} {'C vs E':<12}")
    print("-" * 110)

    metrics = [
        ("Peak ICP (mmHg)",              "metric_1_peak_icp_mmhg",              False),
        ("Time >20 mmHg (sec)",          "metric_2_time_above_20_mmhg_sec",     False),
        ("Drainage capacity (%)",        "metric_3_drainage_capacity_percent",  True),
        ("Time to failure (hr)",         "metric_4_time_to_critical_failure_hr", True),
        ("Intervention count",           "metric_5_intervention_count",         False),
        ("Controller energy (chg/hr)",   "metric_6_controller_energy_changes_per_hr", False),
    ]

    avgs = {}
    for sc in scenarios:
        sc_results = [r for r in all_results if r["scenario"] == sc]
        avgs[sc] = {key: sum(r[key] for r in sc_results) / len(sc_results) for _, key, _ in metrics}

    for label, key, higher_is_better in metrics:
        vals = {sc: avgs[sc].get(key, float("nan")) for sc in scenarios}
        a, b, c = vals.get("A_conventional", float("nan")), vals.get("B_reactive", float("nan")), vals.get("C_predictive", float("nan"))
        d, e = vals.get("D_predictive_closed_loop", float("nan")), vals.get("E_oracle", float("nan"))

        def fmt(v):
            if v != v:  # NaN
                return "N/A"
            if abs(v) > 100:
                return f"{v:.0f}"
            return f"{v:.1f}"

        c_vs_d = c - d if c == c and d == d else float("nan")
        c_vs_e = c - e if c == c and e == e else float("nan")

        def fmt_delta(delta, higher_is_better):
            if delta != delta:
                return "N/A"
            sign = "+" if delta >= 0 else ""
            better = (delta > 0 and higher_is_better) or (delta < 0 and not higher_is_better)
            tag = " BETTER" if better and abs(delta) > 0.01 else ""
            return f"{sign}{fmt(delta)}{tag}"

        print(f"{label:<35} {fmt(a):<10} {fmt(b):<10} {fmt(c):<10} {fmt(d):<10} {fmt(e):<10} {fmt_delta(c_vs_d, higher_is_better):<12} {fmt_delta(c_vs_e, higher_is_better):<12}")

    print()
    print("=" * 110)
    print("CENTRAL QUESTIONS — ANSWERS")
    print("=" * 110)

    c_tfail = avgs["C_predictive"]["metric_4_time_to_critical_failure_hr"]
    d_tfail = avgs["D_predictive_closed_loop"]["metric_4_time_to_critical_failure_hr"]
    e_tfail = avgs["E_oracle"]["metric_4_time_to_critical_failure_hr"]
    c_peak = avgs["C_predictive"]["metric_1_peak_icp_mmhg"]
    d_peak = avgs["D_predictive_closed_loop"]["metric_1_peak_icp_mmhg"]
    e_peak = avgs["E_oracle"]["metric_1_peak_icp_mmhg"]

    print(f"""
QUESTION 1: Does C (predictive isolation) outperform D (predictive closed-loop WITHOUT isolation)?
  Time to failure:  C={c_tfail:.2f}h vs D={d_tfail:.2f}h  → C {'better' if c_tfail > d_tfail else 'worse'} by {abs(c_tfail-d_tfail):.2f}h ({abs(c_tfail-d_tfail)/max(d_tfail,0.01)*100:.0f}%)
  Peak ICP:         C={c_peak:.1f} vs D={d_peak:.1f} mmHg  → C {'better' if c_peak < d_peak else 'worse'} by {abs(c_peak-d_peak):.1f} mmHg

QUESTION 2: How much of E's (oracle) benefit does C capture?
  Time to failure:  C={c_tfail:.2f}h vs E={e_tfail:.2f}h  → C captures {c_tfail/max(e_tfail,0.01)*100:.0f}% of oracle benefit
  Peak ICP:         C={c_peak:.1f} vs E={e_peak:.1f} mmHg  → C captures {(e_peak-c_peak)/max(e_peak-20,0.01)*100:.0f}% of oracle ICP reduction
""")

    # Honest verdict
    c_beats_d = (c_tfail > d_tfail) and (c_peak <= d_peak)
    c_captures_majority = (c_tfail / max(e_tfail, 0.01)) > 0.5

    if c_beats_d:
        print("VERDICT Q1: C's ISOLATION mechanism adds value beyond D's closed-loop modulation.")
        print("  P-01's value proposition is the ISOLATION mechanism, not just prediction.")
    else:
        print("VERDICT Q1: C does NOT outperform D. The ISOLATION mechanism does NOT add value")
        print("  beyond generic predictive closed-loop control. P-01's value proposition is NOT supported.")

    if c_captures_majority:
        print(f"VERDICT Q2: C captures {c_tfail/max(e_tfail,0.01)*100:.0f}% of oracle benefit — majority of theoretically available benefit.")
    else:
        print(f"VERDICT Q2: C captures only {c_tfail/max(e_tfail,0.01)*100:.0f}% of oracle benefit — significant headroom remains.")

    print()
    print("HONEST DISCLOSURE (Article XXVIII):")
    print("  - This is a MODEL-VS-MODEL comparison, NOT clinical evidence.")
    print("  - 59 mmHg (Arm A) is the simulator's single-segment baseline, NOT 'current standard of care.'")
    print("  - Clinical peak ICP for shunt failure requires bench + animal + human measurement.")
    print("  - The 7-9x result (R278) is a model result. Clinical benefit is NOT claimed.")
    print("  - Arm D is our reproduction of the strongest published approach (US20210338992A1 + 2023 ML study).")
    print("    It is NOT the actual published system — it is our simulation of that approach.")
    print("  - Arm E (oracle) is a theoretical upper bound, not a realizable controller.")

    out = os.path.join(here, f"p01_v1_2_ABCDE_comparison_results_{args.attack}.json")
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nWrote {len(all_results)} runs to {out}")


if __name__ == "__main__":
    main()

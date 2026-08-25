"""
P-01 V1.1 — A/B/C Comparison
=============================

R278 directive: "Do not tune the simulator until it passes. Instead,
create Version 1.1 around the actual finding."

This file extends 05_simulator.py (V1.0, frozen at R277 commit 5e7cae7)
with three changes:

1. FIXED: "reactive" isolation mode now isolates on ACTUAL FAILURE
   (G_obs < 10% of healthy), not on trend prediction. V1.0's
   "noprediction" scenario was mis-specified — it still used the
   trend predictor for isolation. This made B (reactive) look identical
   to C (predictive), which is not a fair comparison.

2. ADDED: 6 metrics per the CEO's R278 directive:
   - peak ICP
   - time above 20 mmHg threshold
   - preserved drainage capacity (% of target Q achieved)
   - time to critical failure
   - number of interventions (isolation events)
   - controller energy (alpha changes per hour)

3. ADDED: A/B/C comparison output answering the central buyer question:
   > Does prediction materially outperform ordinary redundancy?

   A = conventional single-path (1 segment, no isolation)
   B = reactive multi-path (4 segments, isolate on actual failure)
   C = predictive isolation + redistribution (4 segments, isolate on trend)

The physics model, controller gains, sensor noise, and occlusion model
are UNCHANGED from V1.0. Per Article XXX (never optimize the evaluator),
we do NOT tune the simulator to make C win. If C does not materially
outperform B, that is the finding.

Constitutional basis:
- Article XXX: this script tries to break the prediction claim, not flatter it
- Article XXXI: V1.0 is preserved in git history; V1.1 documents what changed
- Article XXVIII: the result determines whether P-01's value proposition holds

Run:
    python 06_ABC_comparison.py
    python 06_ABC_comparison.py --seeds 42 43 44 45 46 47 48 49 50
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

# Import V1.0 physics, constants, and dataclasses
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_v10 = import_module("05_simulator")

# Re-export V1.0 constants for local reference
P_MIN_MMHG       = _v10.P_MIN_MMHG
P_MAX_MMHG       = _v10.P_MAX_MMHG
P_TARGET_MMHG    = _v10.P_TARGET_MMHG
F_MAX_PER_SEG    = _v10.F_MAX_PER_SEG
Q_PRODUCTION_ML_MIN = _v10.Q_PRODUCTION_ML_MIN
G_HEALTHY        = _v10.G_HEALTHY
DT_SEC           = _v10.DT_SEC
N_STEPS          = _v10.N_STEPS
SENSOR_NOISE_P_SIGMA = _v10.SENSOR_NOISE_P_SIGMA
SENSOR_NOISE_F_SIGMA = _v10.SENSOR_NOISE_F_SIGMA
PREDICTOR_WINDOW_SEC = _v10.PREDICTOR_WINDOW_SEC
K_OCCL_DEFAULT   = _v10.K_OCCL_DEFAULT

SegmentState     = _v10.SegmentState
estimate_occlusion_probability = _v10.estimate_occlusion_probability
true_conductance = _v10.true_conductance
sensor_reading   = _v10.sensor_reading


# ---------------------------------------------------------------------------
# V1.1 extensions
# ---------------------------------------------------------------------------

@dataclass
class SimConfigV11:
    n_segments: int = 4
    seed: int = 42
    scenario: str = "C_predictive"   # A_conventional | B_reactive | C_predictive
    k_occl: float = K_OCCL_DEFAULT
    lesion_onset_window_hr: tuple = (2.0, 18.0)
    n_lesions: int = 2
    sensor_noise: bool = True
    actuator_delay: bool = True
    # isolation_mode replaces enable_predictor + enable_isolation
    # "none":      no isolation ever (A_conventional)
    # "reactive":  isolate when G_obs < 10% of G_HEALTHY (actual failure)
    # "predictive": isolate when trend predictor fires (C_predictive)
    isolation_mode: str = "predictive"


@dataclass
class SimResultV11:
    scenario: str
    seed: int
    # --- 6 metrics per CEO R278 directive ---
    metric_1_peak_icp_mmhg: float
    metric_2_time_above_20_mmhg_sec: float
    metric_3_drainage_capacity_percent: float
    metric_4_time_to_critical_failure_hr: float
    metric_5_intervention_count: int
    metric_6_controller_energy_changes_per_hr: float
    # --- additional diagnostics ---
    invariant_1_held: bool
    invariant_2_held: bool
    survival: bool
    icp_min: float
    icp_max: float
    isolation_count: int
    prediction_lead_time_sec_avg: Optional[float]
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# V1.1 allocator — distinguishes reactive from predictive isolation
# ---------------------------------------------------------------------------

REACTIVE_FAILURE_THRESHOLD = 0.10   # G_obs < 10% of G_HEALTHY = actual failure
PREDICTIVE_ISOLATE_THRESHOLD = 0.4  # trend predictor P(occl) >= 0.4

def v11_allocator(segs: List[SegmentState],
                  p_obs: float,
                  F_obs: List[float],
                  cfg: SimConfigV11) -> Tuple[List[float], int]:
    """
    V1.1 allocator. Returns (alpha_commands, interventions_this_step).

    Three isolation modes:
      "none":       no isolation. All segments stay active until they die.
      "reactive":   isolate when G_obs_i < 10% of G_HEALTHY (segment is dead).
      "predictive": isolate when trend predictor P(occl) >= 0.4 (segment is dying).

    The PI controller and INV-2 cap logic are UNCHANGED from V1.0.
    """
    n = len(segs)
    interventions = 0

    # --- Isolation decisions ---
    if cfg.isolation_mode == "none":
        pass  # never isolate

    elif cfg.isolation_mode == "reactive":
        # Isolate only on ACTUAL failure: G_obs has dropped below 10% of healthy
        for i, s in enumerate(segs):
            if s.isolated:
                continue
            # Compute current observed conductance from last history entry
            if len(s.history_G) > 0:
                g_obs_now = s.history_G[-1]
            else:
                g_obs_now = G_HEALTHY  # haven't measured yet
            if g_obs_now < REACTIVE_FAILURE_THRESHOLD * G_HEALTHY:
                s.isolated = True
                s.isolation_time_sec = None  # filled by caller
                interventions += 1

    elif cfg.isolation_mode == "predictive":
        # Isolate on trend prediction (V1.0 behavior)
        p_occl = [estimate_occlusion_probability(s, 0.0) for s in segs]
        for i, s in enumerate(segs):
            if s.isolated:
                continue
            if p_occl[i] >= PREDICTIVE_ISOLATE_THRESHOLD:
                s.isolated = True
                s.isolation_time_sec = None
                interventions += 1

    # --- Among survivors, distribute alpha (same PI controller as V1.0) ---
    survivors = [i for i, s in enumerate(segs) if not s.isolated]
    if not survivors:
        return [0.0] * n, interventions

    K_p = 0.020  # UNCHANGED from V1.0 — do NOT tune to pass (Article XXX)
    g_total_target = (Q_PRODUCTION_ML_MIN / P_TARGET_MMHG) + K_p * (p_obs - P_TARGET_MMHG)
    g_total_min = Q_PRODUCTION_ML_MIN / P_MAX_MMHG
    g_total_max = Q_PRODUCTION_ML_MIN / P_MIN_MMHG
    g_total_target = max(g_total_min, min(g_total_max, g_total_target))

    if p_obs > 0.1:
        alpha_inv2_cap = F_MAX_PER_SEG / (G_HEALTHY * p_obs)
    else:
        alpha_inv2_cap = 1.0
    alpha_inv2_cap = max(0.0, min(1.0, alpha_inv2_cap))

    alpha_per_survivor_uncapped = g_total_target / (G_HEALTHY * len(survivors))
    alpha_per_survivor = max(0.0, min(alpha_inv2_cap, alpha_per_survivor_uncapped))

    alpha_cmd = [0.0] * n
    for i in survivors:
        alpha_cmd[i] = alpha_per_survivor

    return alpha_cmd, interventions


# ---------------------------------------------------------------------------
# V1.1 simulation loop with 6-metric tracking
# ---------------------------------------------------------------------------

def run_v11(cfg: SimConfigV11) -> SimResultV11:
    random.seed(cfg.seed)

    segs = [SegmentState(idx=i, n_segments_total=cfg.n_segments) for i in range(cfg.n_segments)]

    # Schedule lesions (same as V1.0)
    lesion_times = sorted(random.uniform(cfg.lesion_onset_window_hr[0],
                                         cfg.lesion_onset_window_hr[1])
                          for _ in range(cfg.n_lesions))
    for t_hr, seg_idx in zip(lesion_times, range(cfg.n_lesions)):
        segs[seg_idx].lesion_start_sec = t_hr * 3600.0
        segs[seg_idx].occlusion_active = True

    # 6-metric trackers
    icp_max = float("-inf")
    icp_min = float("inf")
    time_above_20_sec = 0.0
    drainage_achieved_ml = 0.0       # integrated actual drainage
    drainage_target_ml = Q_PRODUCTION_ML_MIN * (N_STEPS * DT_SEC / 60.0)  # target = CSF production
    time_to_critical_failure_sec = N_STEPS * DT_SEC  # default: survived full run
    intervention_count_total = 0
    alpha_change_count = 0
    prev_alpha = [s.alpha for s in segs]

    # INV trackers
    icp_violation_total = 0.0
    overload_events = 0
    in_overload = [False] * cfg.n_segments
    in_icp_violation = False

    prediction_lead_times: List[float] = []
    survival = True
    notes: List[str] = []

    for step in range(N_STEPS):
        t_sec = step * DT_SEC

        # Actuator delay
        for s in segs:
            s.alpha_delayed = s.alpha

        # Plant step
        G = [true_conductance(s, t_sec, cfg.k_occl) for s in segs]
        G_sum = sum(G)
        if G_sum <= 1e-9:
            p_true = 10.0 * P_MAX_MMHG
        else:
            p_true = Q_PRODUCTION_ML_MIN / G_sum
        F_true = [g * p_true for g in G]

        # Sensor
        if cfg.sensor_noise:
            p_obs = p_true + random.gauss(0, SENSOR_NOISE_P_SIGMA)
            F_obs = [f + random.gauss(0, SENSOR_NOISE_F_SIGMA) for f in F_true]
        else:
            p_obs, F_obs = p_true, list(F_true)

        # Record observed conductance for predictor
        for i, s in enumerate(segs):
            s.history_F.append(F_obs[i])
            s.history_P.append(p_obs)
            if abs(p_obs) > 1e-3:
                g_obs_i = max(0.0, F_obs[i] / p_obs)
            else:
                g_obs_i = 0.0
            s.history_G.append(g_obs_i)

        # Controller
        alpha_cmd, interventions_this_step = v11_allocator(segs, p_obs, F_obs, cfg)
        intervention_count_total += interventions_this_step

        # Apply new alpha
        for i, s in enumerate(segs):
            if not s.isolated:
                s.alpha = alpha_cmd[i]
            else:
                s.alpha = 0.0

            # Count significant alpha changes (controller energy proxy)
            # "Significant" = change > 5% of full range
            if abs(s.alpha - prev_alpha[i]) > 0.05:
                alpha_change_count += 1
            prev_alpha[i] = s.alpha

        # Isolation timing bookkeeping
        for s in segs:
            if s.isolated and s.isolation_time_sec is None:
                s.isolation_time_sec = t_sec
                if s.occlusion_active:
                    catastrophic_time = s.lesion_start_sec + (math.log(0.1) / -cfg.k_occl)
                    lead = catastrophic_time - t_sec
                    if lead > 0:
                        prediction_lead_times.append(lead)

        # --- 6-metric updates ---
        # Metric 1: peak ICP
        icp_max = max(icp_max, p_true)
        icp_min = min(icp_min, p_true)

        # Metric 2: time above 20 mmHg
        if p_true > P_MAX_MMHG:
            time_above_20_sec += DT_SEC

        # Metric 3: drainage capacity (actual drainage / target)
        actual_drainage_this_step = sum(F_true) * DT_SEC / 60.0  # mL
        drainage_achieved_ml += actual_drainage_this_step

        # Metric 4: time to critical failure
        # Critical failure = ICP out of [P_MIN, P_MAX] for >1 hour cumulative
        if p_true < P_MIN_MMHG or p_true > P_MAX_MMHG:
            if not in_icp_violation:
                in_icp_violation = True
            icp_violation_total += DT_SEC
        else:
            in_icp_violation = False

        # Metric 5: intervention count (tracked above)

        # INV-2 check
        for i, s in enumerate(segs):
            if not s.isolated and F_true[i] > F_MAX_PER_SEG + 1e-6:
                if not in_overload[i]:
                    overload_events += 1
                    in_overload[i] = True
            else:
                in_overload[i] = False

        # Catastrophic failure check
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

    # --- Compute final 6 metrics ---
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
# A/B/C scenario presets
# ---------------------------------------------------------------------------

def make_cfg_v11(scenario: str, seed: int) -> SimConfigV11:
    if scenario == "A_conventional":
        # 1 segment, no isolation. When it occludes, P_ICP rises uncontrollably.
        return SimConfigV11(scenario="A_conventional", seed=seed,
                            n_segments=1, n_lesions=1,
                            isolation_mode="none")
    elif scenario == "B_reactive":
        # 4 segments, isolate on ACTUAL failure (G < 10% of healthy).
        # This is "ordinary redundancy" — no prediction, just backup paths.
        return SimConfigV11(scenario="B_reactive", seed=seed,
                            n_segments=4, n_lesions=2,
                            isolation_mode="reactive")
    elif scenario == "C_predictive":
        # 4 segments, isolate on trend prediction (P(occl) >= 0.4).
        # This is the full P-01 system.
        return SimConfigV11(scenario="C_predictive", seed=seed,
                            n_segments=4, n_lesions=2,
                            isolation_mode="predictive")
    else:
        raise ValueError(f"Unknown scenario: {scenario}")


# ---------------------------------------------------------------------------
# Main: run A/B/C comparison
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="P-01 V1.1 A/B/C Comparison")
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--scenario", default=None,
                    choices=["A_conventional", "B_reactive", "C_predictive"],
                    help="Run single scenario (default: run all 3)")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    scenarios = ["A_conventional", "B_reactive", "C_predictive"] if args.scenario is None else [args.scenario]

    all_results = []
    print("=" * 90)
    print("P-01 V1.1 — A/B/C COMPARISON")
    print("Central question: Does prediction materially outperform ordinary redundancy?")
    print("=" * 90)
    print()

    for sc in scenarios:
        print(f"--- {sc} ---")
        for sd in args.seeds:
            cfg = make_cfg_v11(sc, sd)
            r = run_v11(cfg)
            all_results.append(asdict(r))
            print(f"  seed={sd}: peak={r.metric_1_peak_icp_mmhg:6.1f}mmHg  "
                  f"t>20={r.metric_2_time_above_20_mmhg_sec:7.0f}s  "
                  f"drain={r.metric_3_drainage_capacity_percent:5.1f}%  "
                  f"t_fail={r.metric_4_time_to_critical_failure_hr:5.2f}h  "
                  f"interv={r.metric_5_intervention_count}  "
                  f"alpha/hr={r.metric_6_controller_energy_changes_per_hr:6.1f}  "
                  f"surv={'Y' if r.survival else 'N'}")
        print()

    # --- Comparison table ---
    print("=" * 90)
    print("A/B/C COMPARISON TABLE (mean across seeds)")
    print("=" * 90)
    print(f"{'Metric':<40} {'A (single)':<15} {'B (reactive)':<15} {'C (predictive)':<15} {'B vs A':<12} {'C vs B':<12}")
    print("-" * 90)

    metrics = [
        ("Peak ICP (mmHg)",                    "metric_1_peak_icp_mmhg",              False),  # lower is better
        ("Time above 20 mmHg (sec)",           "metric_2_time_above_20_mmhg_sec",     False),
        ("Drainage capacity (%)",              "metric_3_drainage_capacity_percent",  True),   # higher is better
        ("Time to critical failure (hr)",      "metric_4_time_to_critical_failure_hr", True),
        ("Intervention count",                 "metric_5_intervention_count",         False),
        ("Controller energy (alpha chg/hr)",   "metric_6_controller_energy_changes_per_hr", False),
    ]

    for label, key, higher_is_better in metrics:
        vals = {}
        for sc in ["A_conventional", "B_reactive", "C_predictive"]:
            sc_results = [r for r in all_results if r["scenario"] == sc]
            if sc_results:
                vals[sc] = sum(r[key] for r in sc_results) / len(sc_results)
            else:
                vals[sc] = float("nan")

        a, b, c = vals["A_conventional"], vals["B_reactive"], vals["C_predictive"]
        b_vs_a = b - a
        c_vs_b = c - b

        def fmt(v):
            if isinstance(v, float) and abs(v) > 100:
                return f"{v:.0f}"
            return f"{v:.1f}"

        def fmt_delta(d, higher_is_better):
            sign = "+" if d >= 0 else ""
            better = (d > 0 and higher_is_better) or (d < 0 and not higher_is_better)
            tag = " BETTER" if better and abs(d) > 0.01 * abs(a if a else 1) else ""
            return f"{sign}{fmt(d)}{tag}"

        print(f"{label:<40} {fmt(a):<15} {fmt(b):<15} {fmt(c):<15} {fmt_delta(b_vs_a, higher_is_better):<12} {fmt_delta(c_vs_b, higher_is_better):<12}")

    print()
    print("=" * 90)
    print("CENTRAL BUYER QUESTION: Does prediction materially outperform redundancy?")
    print("=" * 90)

    # Compute whether C materially outperforms B
    c_peak = sum(r["metric_1_peak_icp_mmhg"] for r in all_results if r["scenario"] == "C_predictive") / len(args.seeds)
    b_peak = sum(r["metric_1_peak_icp_mmhg"] for r in all_results if r["scenario"] == "B_reactive") / len(args.seeds)
    c_t20 = sum(r["metric_2_time_above_20_mmhg_sec"] for r in all_results if r["scenario"] == "C_predictive") / len(args.seeds)
    b_t20 = sum(r["metric_2_time_above_20_mmhg_sec"] for r in all_results if r["scenario"] == "B_reactive") / len(args.seeds)
    c_drain = sum(r["metric_3_drainage_capacity_percent"] for r in all_results if r["scenario"] == "C_predictive") / len(args.seeds)
    b_drain = sum(r["metric_3_drainage_capacity_percent"] for r in all_results if r["scenario"] == "B_reactive") / len(args.seeds)
    c_tfail = sum(r["metric_4_time_to_critical_failure_hr"] for r in all_results if r["scenario"] == "C_predictive") / len(args.seeds)
    b_tfail = sum(r["metric_4_time_to_critical_failure_hr"] for r in all_results if r["scenario"] == "B_reactive") / len(args.seeds)

    print(f"""
METRIC-BY-METRIC VERDICT (C vs B):
  Peak ICP:           C={c_peak:.1f} vs B={b_peak:.1f} mmHg     → C {'better' if c_peak < b_peak else 'worse'} by {abs(c_peak-b_peak):.1f} mmHg
  Time above 20:      C={c_t20:.0f} vs B={b_t20:.0f} sec         → C {'better' if c_t20 < b_t20 else 'worse'} by {abs(c_t20-b_t20):.0f} sec
  Drainage capacity:  C={c_drain:.1f}% vs B={b_drain:.1f}%       → C {'better' if c_drain > b_drain else 'worse'} by {abs(c_drain-b_drain):.1f}%
  Time to failure:    C={c_tfail:.2f}h vs B={b_tfail:.2f}h       → C {'better' if c_tfail > b_tfail else 'worse'} by {abs(c_tfail-b_tfail):.2f}h
""")

    # Honest verdict
    c_wins = sum([
        c_peak < b_peak,
        c_t20 < b_t20,
        c_drain > b_drain,
        c_tfail > b_tfail,
    ])

    if c_wins >= 3:
        print(f"VERDICT: C (predictive) outperforms B (reactive) on {c_wins}/4 primary metrics.")
        print("PREDICTION MATERIALLY OUTPERFORMS REDUNDANCY in this model.")
        print("This supports P-01's value proposition — with the caveat that neither system")
        print("meets 24h survival, so the advantage is in degree of failure, not in prevention.")
    elif c_wins <= 1:
        print(f"VERDICT: C (predictive) does NOT outperform B (reactive) — wins only {c_wins}/4 metrics.")
        print("PREDICTION DOES NOT MATERIALLY OUTPERFORM REDUNDANCY in this model.")
        print("P-01's value proposition is NOT supported by the simulator. Reformulation required.")
    else:
        print(f"VERDICT: Mixed result — C wins {c_wins}/4 metrics. Prediction has marginal advantage.")
        print("P-01's value proposition is PARTIALLY supported. Buyer must judge if the advantage is material.")

    print()
    print("HONEST DISCLOSURE (Article XXVIII):")
    print("  - This comparison does NOT tune the simulator to make C win (Article XXX).")
    print("  - The physics, controller gains, and occlusion model are UNCHANGED from V1.0.")
    print("  - V1.0's 'noprediction' scenario was mis-specified (still used trend predictor).")
    print("    V1.1 fixes this: B_reactive isolates on actual failure (G < 10% of healthy).")
    print("  - This is a fair A/B/C comparison. The result is the result.")

    # Save results
    out = os.path.join(here, "p01_v1_1_ABC_comparison_results.json")
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nWrote {len(all_results)} runs to {out}")


if __name__ == "__main__":
    main()

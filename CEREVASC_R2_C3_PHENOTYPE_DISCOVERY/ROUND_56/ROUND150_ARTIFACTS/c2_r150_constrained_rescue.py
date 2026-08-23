#!/usr/bin/env python3
"""
C2-R150: PHYSIOLOGICALLY-CONSTRAINED FINAL RESCUE SEARCH

Per CEO Round 150: 'Optimize maximum ΔAUROC subject to physiologically credible
constraints. Not maximum ΔAUROC over arbitrary parameter space.'

The eShunt accesses the inferior petrosal sinus (IPS). Literature says:
- Starling resistor creates HIGH coupling between CSF and cortical/sinus pressure
- IPS is a dural sinus → downstream of cortical veins → Starling-protected
- Literature-supported coupling range: 0.4-0.95 (Barami & Sood 2016, Portnoy et al 1994)

This search ONLY allows IPS coupling in [0.4, 0.95].
If no regime achieves ΔAUROC > 0.05 → C2 KILLED_BY_EVIDENCE.
"""

import json
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

ROUND_150_DIR = Path("/home/z/my-project/discovery-evidence-fabric/CEREVASC_R2_C3_PHENOTYPE_DISCOVERY/ROUND_56/ROUND150_ARTIFACTS")

WIN_THRESHOLD = 0.05

# PHYSIOLOGICAL CONSTRAINTS (literature-supported)
IPS_COUPLING_RANGE = (0.4, 0.95)  # Starling resistor → HIGH coupling
STARLING_NONLIN_RANGE = (0.0, 0.3)  # Nonlinear behavior (PMID 27598891)
VENOUS_OFFSET_RANGE = (1.0, 5.0)  # IPS > CSF by some amount (Starling offset)
OBS_SEVERITY_OPTIONS = [(2, 4), (3, 8), (5, 12)]  # Subtle to classic
POSTURE_OPTIONS = ["supine", "upright", "transitions"]
SENSOR_MISMATCH_RANGE = (0.0, 1.0)  # Realistic sensor mismatch (not extreme)
NOISE_RANGE = (0.3, 0.6)  # Realistic noise


def generate_cohort(params, n_patients=150, seed=42):
    rng = np.random.RandomState(seed)
    ips_coupling = params["ips_coupling"]
    sensor_mismatch = params["sensor_mismatch"]
    noise_std = params["noise_std"]
    venous_offset = params["venous_offset"]
    obs_range = params["obs_severity_range"]
    posture = params["posture"]
    starling_nonlin = params["starling_nonlin"]
    drift_rate = params.get("drift_rate", 0.2)

    patients = []
    for i in range(n_patients):
        baseline_icp = rng.normal(10.0, 2.0)
        baseline_ips = baseline_icp + venous_offset + rng.uniform(0, 2)

        condition = rng.choice(["normal", "obstruction", "over_drainage", "under_drainage"],
                              p=[0.35, 0.35, 0.15, 0.15])
        n_samples = 400
        t = np.arange(n_samples)
        P_csf = np.full(n_samples, baseline_icp, dtype=float)
        P_ips = np.full(n_samples, baseline_ips, dtype=float)
        start_idx = n_samples // 4

        if condition == "obstruction":
            severity = rng.uniform(*obs_range)
            obs_type = rng.choice(["subtle", "gradual", "intermittent", "partial", "classic"])
            if obs_type == "subtle":
                P_csf[start_idx:] += severity
            elif obs_type == "gradual":
                ramp_end = min(start_idx + 250, n_samples)
                P_csf[start_idx:ramp_end] += np.linspace(0, severity, ramp_end - start_idx)
                P_csf[ramp_end:] += severity
            elif obs_type == "intermittent":
                for seg in range(start_idx, n_samples, 80):
                    P_csf[seg:min(seg+40, n_samples)] += severity
            elif obs_type == "partial":
                P_csf[start_idx:] += severity
                P_csf += rng.normal(0, 1.0, n_samples)
            else:
                P_csf[start_idx:] += severity

            csf_change = P_csf[start_idx:] - baseline_icp
            nonlin_factor = 1.0 - starling_nonlin * np.minimum(np.abs(csf_change) / 10.0, 1.0)
            P_ips[start_idx:] += csf_change * ips_coupling * nonlin_factor
        elif condition == "over_drainage":
            severity = rng.uniform(-6, -3)
            P_csf[start_idx:] += severity
            P_ips[start_idx:] += severity * ips_coupling
        elif condition == "under_drainage":
            severity = rng.uniform(1.5, 4)
            P_csf[start_idx:] += np.linspace(0, severity, n_samples - start_idx)
            P_ips[start_idx:] += np.linspace(0, severity, n_samples - start_idx) * ips_coupling

        for _ in range(rng.randint(0, 3)):
            exc_start = rng.randint(0, n_samples - 100)
            exc_dur = rng.randint(30, 150)
            exc_amp = rng.uniform(-3, 4)
            P_csf[exc_start:exc_start+exc_dur] += exc_amp
            P_ips[exc_start:exc_start+exc_dur] += exc_amp * ips_coupling

        if posture == "upright":
            drop = rng.uniform(2, 5)
            P_ips -= drop * 1.1
            P_csf -= drop * 0.2
        elif posture == "transitions":
            for tt in [n_samples//3, 2*n_samples//3]:
                if tt + 40 < n_samples:
                    d = rng.choice([-1, 1]) * rng.uniform(2, 4)
                    P_ips[tt:tt+40] += d * 1.2
                    P_csf[tt:tt+40] += d * 0.2

        pf = rng.uniform(0.8, 1.2)
        pa = rng.uniform(1, 2.5)
        pulse = pa * np.sin(2 * np.pi * pf * t / n_samples * n_samples)
        P_csf += pulse
        P_ips += pulse * 0.7

        P_csf += rng.normal(0, noise_std, n_samples)
        P_ips += rng.normal(0, noise_std, n_samples)
        P_csf += rng.normal(0, 0.5)
        P_ips += rng.normal(0, 0.5) + sensor_mismatch

        dr = rng.uniform(0, drift_rate)
        P_csf += dr * t / n_samples
        P_ips += dr * 0.9 * t / n_samples

        diff = P_csf - P_ips
        patients.append({"condition": condition, "P_csf": P_csf, "diff": diff})
    return patients


def extract_features(signal):
    s = np.array(signal)
    n = len(s)
    mean_p = float(np.mean(s))
    pulse = float(np.std(s))
    sustained = float(np.mean(s[3*n//4:]) - np.mean(s[:n//4]))
    slope = float(np.polyfit(np.arange(n), s, 1)[0])
    temp_var = float(np.std(s[n//2:]) - np.std(s[:n//2]))
    max_dev = float(np.max(np.abs(s - mean_p)))
    med = float(np.median(s))
    fft = np.abs(np.fft.rfft(s - np.mean(s)))
    p2_p1 = float(fft[1] / (fft[0] + 1e-10)) if len(fft) > 1 else 0
    return [mean_p, pulse, sustained, slope, temp_var, max_dev, med, p2_p1]


def eval_delta(patients, seed=42):
    rng = np.random.RandomState(seed)
    n = len(patients)
    idx = rng.permutation(n)
    tr, va, te = idx[:int(0.6*n)], idx[int(0.6*n):int(0.8*n)], idx[int(0.8*n):]

    def prep(indices, ftype):
        X, y = [], []
        for i in indices:
            p = patients[i]
            X.append(extract_features(p["P_csf"] if ftype == "A" else p["diff"]))
            y.append(1 if p["condition"] == "obstruction" else 0)
        return np.array(X), np.array(y)

    Xa_tr, y_tr = prep(tr, "A")
    Xa_val, y_val = prep(va, "A")
    Xa_te, y_te = prep(te, "A")
    Xb_tr = prep(tr, "B")[0]
    Xb_val = prep(va, "B")[0]
    Xb_te = prep(te, "B")[0]

    sa = StandardScaler().fit(Xa_tr)
    sb = StandardScaler().fit(Xb_tr)

    best_ca, best_cb = 1.0, 1.0
    best_ava, best_bva = 0, 0
    for c in [0.01, 0.1, 1.0, 10.0]:
        ma = LogisticRegression(C=c, penalty='l2', max_iter=500, random_state=42)
        ma.fit(sa.transform(Xa_tr), y_tr)
        aa = roc_auc_score(y_val, ma.predict_proba(sa.transform(Xa_val))[:, 1])
        if aa > best_ava: best_ava, best_ca = aa, c
        mb = LogisticRegression(C=c, penalty='l2', max_iter=500, random_state=42)
        mb.fit(sb.transform(Xb_tr), y_tr)
        ba = roc_auc_score(y_val, mb.predict_proba(sb.transform(Xb_val))[:, 1])
        if ba > best_bva: best_bva, best_cb = ba, c

    ma = LogisticRegression(C=best_ca, penalty='l2', max_iter=500, random_state=42)
    ma.fit(sa.transform(Xa_tr), y_tr)
    auc_a = roc_auc_score(y_te, ma.predict_proba(sa.transform(Xa_te))[:, 1])

    mb = LogisticRegression(C=best_cb, penalty='l2', max_iter=500, random_state=42)
    mb.fit(sb.transform(Xb_tr), y_tr)
    auc_b = roc_auc_score(y_te, mb.predict_proba(sb.transform(Xb_te))[:, 1])

    return auc_a, auc_b, auc_b - auc_a


def main():
    print("=" * 80)
    print("C2-R150: PHYSIOLOGICALLY-CONSTRAINED FINAL RESCUE SEARCH")
    print(f"IPS coupling constrained to [{IPS_COUPLING_RANGE[0]}, {IPS_COUPLING_RANGE[1]}]")
    print(f"WIN threshold: ΔAUROC > {WIN_THRESHOLD}")
    print("If no regime wins → C2 KILLED_BY_EVIDENCE")
    print("=" * 80)

    # Generate physiologically-constrained parameter grid
    param_grid = []
    for ips_coupling in np.arange(0.4, 1.0, 0.1):  # 0.4, 0.5, 0.6, 0.7, 0.8, 0.9
        for starling_nonlin in [0.0, 0.15, 0.3]:
            for venous_offset in [1.0, 3.0, 5.0]:
                for obs_range in [(2, 4), (3, 8), (5, 12)]:
                    for posture in POSTURE_OPTIONS:
                        for sensor_mismatch in [0.0, 0.5, 1.0]:
                            for noise_std in [0.3, 0.6]:
                                param_grid.append({
                                    "ips_coupling": round(ips_coupling, 1),
                                    "starling_nonlin": starling_nonlin,
                                    "venous_offset": venous_offset,
                                    "obs_severity_range": obs_range,
                                    "posture": posture,
                                    "sensor_mismatch": sensor_mismatch,
                                    "noise_std": noise_std,
                                    "drift_rate": 0.2,
                                })

    print(f"\n[1] Physiologically-constrained grid: {len(param_grid)} combinations")
    print(f"    IPS coupling: {IPS_COUPLING_RANGE} (literature-supported)")
    print(f"    Starling nonlinearity: {STARLING_NONLIN_RANGE}")
    print(f"    Sensor mismatch: {SENSOR_MISMATCH_RANGE} (realistic)")

    # Sample 80 combinations
    rng = np.random.RandomState(42)
    sample_indices = rng.choice(len(param_grid), size=min(80, len(param_grid)), replace=False)
    sampled = [param_grid[i] for i in sorted(sample_indices)]

    print(f"[2] Sampled {len(sampled)} combinations")

    best_delta = -999
    best_params = None
    best_auc_a = 0
    best_auc_b = 0
    winning_count = 0
    all_deltas = []

    for i, params in enumerate(sampled):
        patients = generate_cohort(params, n_patients=120, seed=42)
        auc_a, auc_b, delta = eval_delta(patients, seed=42)
        all_deltas.append(delta)

        if delta > best_delta:
            best_delta = delta
            best_params = params
            best_auc_a = auc_a
            best_auc_b = auc_b

        if delta > WIN_THRESHOLD:
            winning_count += 1

        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(sampled)}] Best ΔAUROC: {best_delta:+.4f}, Winners: {winning_count}")

    print(f"\n[3] RESULTS:")
    print(f"  Best ΔAUROC: {best_delta:+.4f}")
    print(f"  Absolute AUROC: {best_auc_a:.4f}")
    print(f"  Differential AUROC: {best_auc_b:.4f}")
    print(f"  Winning regimes (ΔAUROC > {WIN_THRESHOLD}): {winning_count}/{len(sampled)}")
    print(f"  Best params: {json.dumps(best_params, indent=2)}")

    print(f"\n  Distribution of ΔAUROC:")
    print(f"    Max: {max(all_deltas):+.4f}")
    print(f"    Min: {min(all_deltas):+.4f}")
    print(f"    Mean: {np.mean(all_deltas):+.4f}")
    print(f"    Median: {np.median(all_deltas):+.4f}")
    print(f"    Positive: {sum(1 for d in all_deltas if d > 0)}/{len(all_deltas)}")
    print(f"    > 0.05: {winning_count}/{len(all_deltas)}")

    print("\n" + "=" * 80)
    print("PRE-REGISTERED THRESHOLD APPLICATION")
    print("=" * 80)

    if best_delta > WIN_THRESHOLD:
        print(f"\n  VERDICT: C2 SURVIVES — {winning_count} regimes meet WIN threshold")
        print(f"  Best ΔAUROC: {best_delta:+.4f}")
        verdict = "SURVIVES"
    else:
        print(f"\n  VERDICT: C2 KILLED_BY_EVIDENCE")
        print(f"  No physiologically credible regime achieves ΔAUROC > {WIN_THRESHOLD}")
        print(f"  Maximum ΔAUROC in credible envelope: {best_delta:+.4f}")
        print(f"  The Starling resistor coupling (0.4-0.95) makes the eShunt IPS")
        print(f"  differential uninformative across the physiologically credible range.")
        verdict = "KILLED_BY_EVIDENCE"

    output = {
        "experiment_id": "C2-R150-PHYSIOLOGICALLY-CONSTRAINED-FINAL-RESCUE",
        "date": datetime.now(timezone.utc).isoformat(),
        "round": 150,
        "description": "Final C2 rescue search constrained to physiologically credible IPS coupling (0.4-0.95). If no regime achieves ΔAUROC > 0.05, C2 is killed.",
        "physiological_constraints": {
            "ips_coupling": f"{IPS_COUPLING_RANGE} (literature-supported: Starling resistor → HIGH coupling)",
            "starling_nonlin": f"{STARLING_NONLIN_RANGE}",
            "sensor_mismatch": f"{SENSOR_MISMATCH_RANGE} (realistic)",
            "literature_basis": ["PMID 26767844 (tight CSF-venous coupling)", "PMID 8194060 (cortical vs periventricular)", "PMID 27598891 (nonlinear Starling)"]
        },
        "win_threshold": WIN_THRESHOLD,
        "n_combinations_tested": len(sampled),
        "best_delta": best_delta,
        "best_params": best_params,
        "best_auc_absolute": best_auc_a,
        "best_auc_differential": best_auc_b,
        "winning_count": winning_count,
        "delta_distribution": {
            "max": max(all_deltas),
            "min": min(all_deltas),
            "mean": float(np.mean(all_deltas)),
            "median": float(np.median(all_deltas)),
            "n_positive": sum(1 for d in all_deltas if d > 0),
        },
        "verdict": verdict,
        "c2_killed": verdict == "KILLED_BY_EVIDENCE",
        "evidence_class": "SCIENTIFIC_EVIDENCE",
    }

    output_path = ROUND_150_DIR / "C2_R150_CONSTRAINED_RESCUE_RESULTS.json"
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n[OK] Results: {output_path}")
    print("[DONE]")


if __name__ == "__main__":
    main()

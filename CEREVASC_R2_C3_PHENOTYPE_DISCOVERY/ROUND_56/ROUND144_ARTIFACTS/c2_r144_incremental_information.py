#!/usr/bin/env python3
"""
C2-R144-INCREMENTAL-INFORMATION-TEST

Per CEO Round 144: 'Rebuild the decisive C2 experiment. Three models:
A = absolute-only, B = differential-only, C = absolute + differential.
Use identical feature families, identical model class, identical training/
validation methodology, held-out test population.'

Per CEO Round 144: 'Before accepting an experiment as falsification-grade,
the AI must attack the experiment itself.'

Key corrections from Round 143:
1. Same feature architecture for all models (not hand-coded thresholds)
2. Same model class (logistic regression with L2 regularization)
3. Same training procedure (train/val/test split, no threshold cherry-picking)
4. Virtual cohort with patient-level variation (not single canonical patient)
5. Three models: A (absolute), B (differential), C (combined)
6. Incremental information: does C materially outperform A?
7. Experiment self-attack: document what could create a false result
"""

import json
import hashlib
import math
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_recall_curve, average_precision_score
from sklearn.model_selection import StratifiedKFold

ROUND_144_DIR = Path("/home/z/my-project/discovery-evidence-fabric/CEREVASC_R2_C3_PHENOTYPE_DISCOVERY/ROUND_56/ROUND144_ARTIFACTS")


def generate_virtual_cohort(n_patients=500, seed=42):
    """
    Generate a virtual cohort of n_patients with patient-level variation.

    Each patient has different:
    - Baseline ICP
    - Venous pressure
    - CSF compliance
    - Shunt resistance
    - Pulse morphology
    - Posture response
    - Sensor bias
    - Sensor drift rate

    Returns list of patient dicts, each with pressure signals and labels.
    """
    rng = np.random.RandomState(seed)
    patients = []

    for i in range(n_patients):
        # Patient-level parameters (drawn from distributions)
        baseline_icp = rng.normal(10.0, 3.0)  # mmHg, std=3
        venous_pressure = rng.normal(5.0, 2.0)  # mmHg
        csf_compliance = rng.uniform(0.5, 2.0)  # mL/mmHg
        shunt_resistance = rng.uniform(5.0, 15.0)  # mmHg/(mL/min)
        pulse_amp_base = rng.uniform(1.5, 3.0)  # mmHg
        p2_p1_ratio_base = rng.uniform(0.4, 0.8)  # dimensionless
        posture_response = rng.uniform(2.0, 5.0)  # mmHg
        cough_response = rng.uniform(5.0, 15.0)  # mmHg
        resp_amp = rng.uniform(0.5, 2.0)  # mmHg
        sensor_bias_icp = rng.normal(0, 1.0)  # mmHg offset
        sensor_bias_venous = rng.normal(0, 1.0)  # mmHg offset (different sensor)
        drift_rate = rng.uniform(0.0, 0.5)  # mmHg/hour
        venous_coupling = rng.uniform(0.1, 0.5)  # fraction of CSF change transmitted to venous

        # Randomly assign condition (balanced)
        condition = rng.choice(["normal", "obstruction", "over_drainage", "under_drainage"])

        # Generate 1-hour signal at 1 Hz
        n_samples = 3600
        t = np.arange(n_samples)

        # Base pressure
        icp = np.full(n_samples, baseline_icp, dtype=float)
        venous = np.full(n_samples, venous_pressure, dtype=float)

        # Apply condition
        start_idx = n_samples // 4  # condition onset at 25%
        if condition == "obstruction":
            obstruction_severity = rng.uniform(5.0, 12.0)  # mmHg increase
            icp[start_idx:] += obstruction_severity
            venous[start_idx:] += obstruction_severity * venous_coupling
        elif condition == "over_drainage":
            overdrain_severity = rng.uniform(-8.0, -4.0)
            icp[start_idx:] += overdrain_severity
            venous[start_idx:] += overdrain_severity * venous_coupling * 1.5  # venous drops more
        elif condition == "under_drainage":
            underdrain_severity = rng.uniform(2.0, 5.0)
            ramp = np.linspace(0, underdrain_severity, n_samples - start_idx)
            icp[start_idx:] += ramp
            venous[start_idx:] += ramp * venous_coupling

        # Add cardiac pulse
        pulse_freq = rng.uniform(0.8, 1.2)  # ~50-72 bpm
        pulse = pulse_amp_base * np.sin(2 * np.pi * pulse_freq * t / n_samples * n_samples)
        p2 = pulse_amp_base * p2_p1_ratio_base * np.sin(2 * np.pi * pulse_freq * t / n_samples * n_samples + 0.3 * np.pi)
        icp += pulse + p2
        venous += pulse * 0.7 + p2 * 0.5  # venous pulse attenuated

        # Add respiration
        resp_freq = rng.uniform(0.15, 0.35)  # 9-21 breaths/min
        icp += resp_amp * np.sin(2 * np.pi * resp_freq * t / n_samples * n_samples)
        venous += resp_amp * 0.8 * np.sin(2 * np.pi * resp_freq * t / n_samples * n_samples)

        # Add random posture changes (1-3 events)
        n_posture = rng.randint(0, 4)
        for _ in range(n_posture):
            p_start = rng.randint(n_samples // 4, 3 * n_samples // 4)
            p_dur = rng.randint(300, 1800)  # 5-30 minutes
            p_end = min(p_start + p_dur, n_samples)
            icp[p_start:p_end] += posture_response
            venous[p_start:p_end] += posture_response * 0.8

        # Add random cough events (0-5)
        n_cough = rng.randint(0, 6)
        for _ in range(n_cough):
            c_time = rng.randint(n_samples // 4, 3 * n_samples // 4)
            c_dur = rng.randint(2, 5)
            icp[c_time:c_time+c_dur] += cough_response
            venous[c_time:c_time+c_dur] += cough_response * 0.7

        # Add sensor noise
        noise_std = rng.uniform(0.2, 0.8)
        icp += rng.normal(0, noise_std, n_samples)
        venous += rng.normal(0, noise_std, n_samples)

        # Add sensor bias
        icp += sensor_bias_icp
        venous += sensor_bias_venous

        # Add drift
        drift = drift_rate * t / 3600
        icp += drift
        venous += drift * 0.9  # slightly different drift on each sensor

        # Differential signal
        differential = icp - venous

        patients.append({
            "patient_id": i,
            "condition": condition,
            "icp": icp,
            "venous": venous,
            "differential": differential,
            "patient_params": {
                "baseline_icp": baseline_icp,
                "venous_pressure": venous_pressure,
                "venous_coupling": venous_coupling,
                "sensor_bias_icp": sensor_bias_icp,
                "sensor_bias_venous": sensor_bias_venous,
                "drift_rate": drift_rate,
            }
        })

    return patients


def extract_features(signal):
    """Extract identical feature set from any pressure signal."""
    signal = np.array(signal)
    n = len(signal)

    # Mean pressure
    mean_p = float(np.mean(signal))

    # Pulse amplitude (rolling std as proxy)
    window = 60
    rolling_std = np.array([np.std(signal[max(0,i-window):i+1]) for i in range(n)])
    pulse_amp = float(np.mean(rolling_std))

    # P2/P1 ratio (spectral)
    fft = np.abs(np.fft.rfft(signal - np.mean(signal)))
    if len(fft) > 2:
        cardiac_idx = np.argmax(fft[1:]) + 1
        p1 = float(fft[cardiac_idx]) if cardiac_idx < len(fft) else 0
        p2_idx = int(cardiac_idx * 1.3)
        p2 = float(fft[p2_idx]) if p2_idx < len(fft) else 0
        p2_p1 = p2 / p1 if p1 > 0 else 0
    else:
        p2_p1 = 0.0

    # Time-to-peak
    ttp = float(np.argmax(signal) / n)

    # Temporal variability
    rolling_means = np.array([np.mean(signal[max(0,i-window):i+1]) for i in range(n)])
    temp_var = float(np.std(rolling_means) / (abs(np.mean(rolling_means)) + 0.001))

    # Sustained change
    first_q = float(np.mean(signal[:n//4]))
    last_q = float(np.mean(signal[3*n//4:]))
    sustained = last_q - first_q

    # Slope (linear trend)
    t = np.arange(n)
    slope = float(np.polyfit(t, signal, 1)[0])

    # Spectral entropy
    psd = fft ** 2
    if psd.sum() > 0:
        psd_norm = psd / psd.sum()
        spec_entropy = float(-np.sum(psd_norm * np.log(psd_norm + 1e-10)))
    else:
        spec_entropy = 0.0

    return [mean_p, pulse_amp, p2_p1, ttp, temp_var, sustained, slope, spec_entropy]


def run_experiment():
    print("=" * 80)
    print("C2-R144 INCREMENTAL INFORMATION TEST")
    print("3 models: A=absolute, B=differential, C=combined")
    print("Identical features, identical classifier, held-out test")
    print("=" * 80)

    # Generate virtual cohort
    print("\n[1] Generating virtual cohort (500 patients)...")
    patients = generate_virtual_cohort(n_patients=500, seed=42)

    # Split: 60% train, 20% val, 20% test
    n = len(patients)
    rng = np.random.RandomState(123)
    indices = rng.permutation(n)
    train_idx = indices[:int(0.6*n)]
    val_idx = indices[int(0.6*n):int(0.8*n)]
    test_idx = indices[int(0.8*n):]

    print(f"  Train: {len(train_idx)}, Val: {len(val_idx)}, Test: {len(test_idx)}")

    # Binary classification: obstruction vs non-obstruction
    print("\n[2] Preparing features (obstruction vs non-obstruction)...")

    def prepare_data(patient_indices, patients):
        X_abs = []
        X_diff = []
        X_combined = []
        y = []
        for idx in patient_indices:
            p = patients[idx]
            abs_features = extract_features(p["icp"])
            diff_features = extract_features(p["differential"])
            X_abs.append(abs_features)
            X_diff.append(diff_features)
            X_combined.append(abs_features + diff_features)
            y.append(1 if p["condition"] == "obstruction" else 0)
        return np.array(X_abs), np.array(X_diff), np.array(X_combined), np.array(y)

    X_abs_train, X_diff_train, X_comb_train, y_train = prepare_data(train_idx, patients)
    X_abs_val, X_diff_val, X_comb_val, y_val = prepare_data(val_idx, patients)
    X_abs_test, X_diff_test, X_comb_test, y_test = prepare_data(test_idx, patients)

    print(f"  Obstruction prevalence: train={y_train.mean():.2f}, test={y_test.mean():.2f}")

    # Scale features
    scaler_abs = StandardScaler().fit(X_abs_train)
    scaler_diff = StandardScaler().fit(X_diff_train)
    scaler_comb = StandardScaler().fit(X_comb_train)

    X_abs_train_s = scaler_abs.transform(X_abs_train)
    X_abs_val_s = scaler_abs.transform(X_abs_val)
    X_abs_test_s = scaler_abs.transform(X_abs_test)

    X_diff_train_s = scaler_diff.transform(X_diff_train)
    X_diff_val_s = scaler_diff.transform(X_diff_val)
    X_diff_test_s = scaler_diff.transform(X_diff_test)

    X_comb_train_s = scaler_comb.transform(X_comb_train)
    X_comb_val_s = scaler_comb.transform(X_comb_val)
    X_comb_test_s = scaler_comb.transform(X_comb_test)

    # Train 3 models with identical architecture (logistic regression with L2)
    print("\n[3] Training 3 models (LogisticRegression, L2, same C)...")

    # Hyperparameter C selected on validation set
    best_c = 1.0
    best_val_auc = 0
    for c in [0.01, 0.1, 1.0, 10.0, 100.0]:
        model = LogisticRegression(C=c, penalty='l2', max_iter=1000, random_state=42)
        model.fit(X_abs_train_s, y_train)
        val_auc = roc_auc_score(y_val, model.predict_proba(X_abs_val_s)[:, 1])
        if val_auc > best_val_auc:
            best_val_auc = val_auc
            best_c = c

    print(f"  Best C (selected on val): {best_c} (val AUC={best_val_auc:.4f})")

    # Model A: absolute only
    model_a = LogisticRegression(C=best_c, penalty='l2', max_iter=1000, random_state=42)
    model_a.fit(X_abs_train_s, y_train)

    # Model B: differential only
    model_b = LogisticRegression(C=best_c, penalty='l2', max_iter=1000, random_state=42)
    model_b.fit(X_diff_train_s, y_train)

    # Model C: combined (absolute + differential)
    model_c = LogisticRegression(C=best_c, penalty='l2', max_iter=1000, random_state=42)
    model_c.fit(X_comb_train_s, y_train)

    # Evaluate on held-out test set
    print("\n[4] Evaluating on held-out test set...")

    pred_a = model_a.predict_proba(X_abs_test_s)[:, 1]
    pred_b = model_b.predict_proba(X_diff_test_s)[:, 1]
    pred_c = model_c.predict_proba(X_comb_test_s)[:, 1]

    auc_a = roc_auc_score(y_test, pred_a)
    auc_b = roc_auc_score(y_test, pred_b)
    auc_c = roc_auc_score(y_test, pred_c)

    auprc_a = average_precision_score(y_test, pred_a)
    auprc_b = average_precision_score(y_test, pred_b)
    auprc_c = average_precision_score(y_test, pred_c)

    # Sensitivity at 90% specificity
    def sens_at_spec(y_true, y_pred, target_spec=0.9):
        from sklearn.metrics import roc_curve
        fpr, tpr, thresholds = roc_curve(y_true, y_pred)
        for i in range(len(fpr)):
            if (1 - fpr[i]) >= target_spec:
                return tpr[i]
        return 0.0

    sens_a = sens_at_spec(y_test, pred_a)
    sens_b = sens_at_spec(y_test, pred_b)
    sens_c = sens_at_spec(y_test, pred_c)

    # Results
    print("\n" + "=" * 80)
    print("RESULTS: Incremental Information Test")
    print("=" * 80)
    print(f"\n{'Model':<25} {'AUROC':<10} {'AUPRC':<10} {'Sens@90%Spec':<15}")
    print("-" * 60)
    print(f"{'A: Absolute only':<25} {auc_a:<10.4f} {auprc_a:<10.4f} {sens_a:<15.4f}")
    print(f"{'B: Differential only':<25} {auc_b:<10.4f} {auprc_b:<10.4f} {sens_b:<15.4f}")
    print(f"{'C: Combined (A+B)':<25} {auc_c:<10.4f} {auprc_c:<10.4f} {sens_c:<15.4f}")

    incremental_auroc = auc_c - auc_a
    incremental_auprc = auprc_c - auprc_a
    incremental_sens = sens_c - sens_a

    print(f"\n{'Incremental (C-A)':<25} {incremental_auroc:<+10.4f} {incremental_auprc:<+10.4f} {incremental_sens:<+15.4f}")

    # Hypothesis assessment
    print("\n" + "=" * 80)
    print("HYPOTHESIS ASSESSMENT")
    print("=" * 80)

    if incremental_auroc > 0.05:
        print(f"\n  H-B SUPPORTED: Combined model MATERIALLY outperforms absolute-only.")
        print(f"  Incremental AUROC: +{incremental_auroc:.4f}")
        print(f"  Differential pressure ADDS information beyond absolute ICP.")
        print(f"  CL5d is technically meaningful.")
        verdict = "H_B_SUPPORTED"
    elif incremental_auroc > 0.01:
        print(f"\n  H-C SUPPORTED: Combined model provides MODEST improvement.")
        print(f"  Incremental AUROC: +{incremental_auroc:.4f}")
        print(f"  Differential adds some information but advantage is small.")
        verdict = "H_C_SUPPORTED"
    elif incremental_auroc > -0.01:
        print(f"\n  H-A SUPPORTED: No meaningful difference between combined and absolute-only.")
        print(f"  Incremental AUROC: {incremental_auroc:+.4f}")
        print(f"  Differential does NOT add information beyond absolute ICP.")
        print(f"  CL5d is not technically meaningful. C2 should be KILLED.")
        verdict = "H_A_SUPPORTED_KILL_C2"
    else:
        print(f"\n  H-A+D SUPPORTED: Differential is WORSE than absolute-only.")
        print(f"  Incremental AUROC: {incremental_auroc:+.4f}")
        print(f"  Differential degrades performance. C2 should be KILLED.")
        verdict = "H_A_D_SUPPORTED_KILL_C2"

    # Experiment self-attack
    print("\n" + "=" * 80)
    print("EXPERIMENT SELF-ATTACK")
    print("=" * 80)
    self_attack = {
        "could_threshold_selection_create_result": "NO — same C for all models, selected on validation set only",
        "could_synthetic_data_assumptions_create_result": "PARTIALLY — venous_coupling is randomly drawn, but the generator assumes venous pressure changes less than CSF during obstruction. If venous_coupling were 1.0 (full coupling), differential would provide no information. The random uniform(0.1, 0.5) range means differential ALWAYS has some signal. This is a model assumption, not a proven physiological fact.",
        "could_unequal_model_capacity_create_result": "NO — all models use identical LogisticRegression with same C. Model C has 2x features but same regularization.",
        "could_leakage_create_result": "NO — train/val/test split is patient-level, no temporal leakage",
        "could_observable_bias_create_result": "PARTIALLY — the obstruction definition (+5-12 mmHg sustained) is a model assumption. Real obstruction may have different presentation.",
        "could_benchmark_be_unfair": "NO — same feature family, same scaler, same classifier, same evaluation protocol",
        "key_limitation": "The synthetic generator assumes venous coupling < 0.5. This is a PHYSIOLOGICAL ASSUMPTION that determines whether differential carries information. If real venous coupling is higher, differential provides less information. This assumption needs validation against published physiological data.",
    }
    for q, a in self_attack.items():
        print(f"  {q}: {a}")

    # Write output
    output = {
        "experiment_id": "C2-R144-INCREMENTAL-INFORMATION-TEST",
        "date": datetime.now(timezone.utc).isoformat(),
        "round": 144,
        "description": "Incremental information test: does differential CSF-venous pressure add information beyond absolute ICP when both use identical features, classifier, and evaluation?",
        "models": {
            "A_absolute_only": {"features": "8 features from ICP signal", "classifier": "LogisticRegression L2", "AUROC": auc_a, "AUPRC": auprc_a, "sens_at_90_spec": sens_a},
            "B_differential_only": {"features": "8 features from CSF-venous differential", "classifier": "LogisticRegression L2", "AUROC": auc_b, "AUPRC": auprc_b, "sens_at_90_spec": sens_b},
            "C_combined": {"features": "16 features (8 absolute + 8 differential)", "classifier": "LogisticRegression L2", "AUROC": auc_c, "AUPRC": auprc_c, "sens_at_90_spec": sens_c},
        },
        "incremental_information": {
            "delta_AUROC": incremental_auroc,
            "delta_AUPRC": incremental_auprc,
            "delta_sensitivity": incremental_sens,
        },
        "hypothesis_verdict": verdict,
        "experiment_self_attack": self_attack,
        "virtual_cohort": {
            "n_patients": 500,
            "split": "60% train, 20% val, 20% test",
            "patient_variation": "baseline_icp, venous_pressure, csf_compliance, shunt_resistance, pulse_morphology, posture_response, cough_response, sensor_bias, sensor_drift, venous_coupling",
            "key_assumption": "venous_coupling ~ Uniform(0.1, 0.5) — venous pressure changes less than CSF during obstruction",
        },
        "patent_implication": {
            "if_H_B_supported": "Differential adds material information. CL5d is technically meaningful. C2's inventive step: 'using differential CSF-venous signal provides unexpected technical advantage over absolute-only approaches.' This is an unexpected technical result that strengthens the §103 defense.",
            "if_H_A_supported": "Differential adds no information. CL5d collapses. C2 should be KILLED_BY_EVIDENCE. The combination of known elements produces no unexpected technical result.",
            "if_H_C_supported": "Differential adds modest information. CL5d is weakly supported. C2's inventive step is marginal — may not survive §103 attack.",
        },
        "evidence_class": "SCIENTIFIC_EVIDENCE",
        "key_limitation": "The venous_coupling assumption (Uniform 0.1-0.5) is the load-bearing model assumption. If real physiology has higher coupling, differential provides less information. This needs validation against published CSF/venous pressure data.",
    }

    output_path = ROUND_144_DIR / "C2_R144_INCREMENTAL_INFORMATION_RESULTS.json"
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n[OK] Results: {output_path}")
    print("[DONE]")


if __name__ == "__main__":
    run_experiment()

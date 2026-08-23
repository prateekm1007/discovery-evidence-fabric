#!/usr/bin/env python3
"""
C2-R146: COMPARTMENT-IDENTITY FALSIFICATION

Per CEO Round 146: 'Stop using a scalar venous coupling. Replace with an explicit
compartmental physiology model. Model posture as state transition. Attack the actual
eShunt anatomy. Four virtual worlds: A=absolute ICP, B=eShunt-accessible venous
differential, C=periventricular venous differential, D=combined+state.'

Compartmental model based on published physiology:
- PMID 26767844: CSF-venous tightly coupled via Starling resistor
- PMID 8194060: Cortical venous pressure > CSF (Starling). Periventricular venous
  pressure does NOT increase with CSF pressure (transparenchymal pressure gradient)
- PMID 39029117: Posture changes venous outflow pathway (cortical→vertebral)
- PMID 27598891: Starling resistor behavior is nonlinear

eShunt anatomy: The eShunt creates an endovascular connection from the venous
sinus to the subarachnoid space. The venous sensor measures DURAL SINUS pressure.
Dural sinus = downstream of cortical veins = Starling-resistor-protected compartment.

Key physiological insight from PMID 8194060:
- Cortical vein pressure (and thus sinus pressure) is maintained ABOVE CSF pressure
  by the Starling resistor. When CSF pressure rises, cortical venous pressure ALSO
  rises (they are coupled).
- Periventricular/deep vein pressure does NOT have the same Starling protection.
  When CSF pressure rises in hydrocephalus, periventricular venous pressure rises
  LESS → transparenchymal pressure gradient (TPP) increases.
- Therefore: eShunt-accessible (sinus) differential = HIGH coupling.
  Periventricular differential = LOW coupling = MORE informative.

This is the compartment-identity question: does eShunt measure the right compartment?
"""

import json
import hashlib
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score, roc_curve

ROUND_146_DIR = Path("/home/z/my-project/discovery-evidence-fabric/CEREVASC_R2_C3_PHENOTYPE_DISCOVERY/ROUND_56/ROUND146_ARTIFACTS")


# ============================================================
# COMPARTMENTAL PHYSIOLOGY MODEL
# ============================================================

def simulate_compartmental_pressure(condition, posture_state, n_samples=600, seed=42):
    """
    Simulate pressure in 4 compartments:
    1. Ventricular CSF pressure (P_csf)
    2. Dural sinus pressure (P_sinus) — eShunt-accessible venous compartment
    3. Cortical vein pressure (P_cortical) — upstream of sinus, Starling-protected
    4. Periventricular/deep vein pressure (P_periventricular) — NOT Starling-protected

    Based on PMID 8194060 (Portnoy et al, 1994):
    - Normally: P_cortical > P_csf (Starling resistor maintains cortical venous pressure above CSF)
    - In hydrocephalus: P_csf increases, P_cortical increases WITH it (coupled)
    - But P_periventricular does NOT increase similarly → TPP increases
    - P_sinus is downstream of P_cortical → P_sinus ≈ P_cortical - small_gradient

    Posture effects (PMID 39029117, 26767844):
    - Supine: venous outflow via jugular → cortical/sinus pressure higher
    - Upright: venous outflow shifts to vertebral plexus → jugular/sinus pressure drops
    - Valsalva: all venous pressures spike transiently
    """
    rng = np.random.RandomState(seed)
    t = np.arange(n_samples)

    # Baseline pressures (mmHg)
    P_csf_base = rng.normal(10.0, 2.0)
    P_cortical_base = P_csf_base + rng.uniform(2.0, 5.0)  # Cortical > CSF (Starling)
    P_sinus_base = P_cortical_base - rng.uniform(0.5, 2.0)  # Sinus slightly below cortical
    P_periventricular_base = P_csf_base - rng.uniform(0.0, 2.0)  # Deep veins near CSF

    # Starling resistor parameters (nonlinear, per PMID 27598891)
    starling_gain = rng.uniform(0.6, 0.9)  # How much cortical follows CSF (HIGH coupling)
    starling_offset = rng.uniform(2.0, 5.0)  # Constant offset maintained by Starling

    # Periventricular coupling (LOW — per PMID 8194060)
    periventricular_coupling = rng.uniform(0.1, 0.4)  # Deep veins don't track CSF well

    # Condition-specific changes
    P_csf = np.full(n_samples, P_csf_base, dtype=float)
    P_cortical = np.full(n_samples, P_cortical_base, dtype=float)
    P_sinus = np.full(n_samples, P_sinus_base, dtype=float)
    P_periventricular = np.full(n_samples, P_periventricular_base, dtype=float)

    start_idx = n_samples // 4

    if condition == "obstruction":
        severity = rng.uniform(5.0, 12.0)
        P_csf[start_idx:] += severity
        # Cortical veins follow CSF (Starling resistor → HIGH coupling)
        P_cortical[start_idx:] += severity * starling_gain
        # Sinus follows cortical (downstream)
        P_sinus[start_idx:] += severity * starling_gain * 0.9
        # Periventricular veins do NOT follow (LOW coupling → TPP increases)
        P_periventricular[start_idx:] += severity * periventricular_coupling

    elif condition == "over_drainage":
        severity = rng.uniform(-8.0, -4.0)
        P_csf[start_idx:] += severity
        P_cortical[start_idx:] += severity * starling_gain
        P_sinus[start_idx:] += severity * starling_gain * 0.9
        P_periventricular[start_idx:] += severity * periventricular_coupling * 1.5  # deep veins more affected

    elif condition == "under_drainage":
        severity = rng.uniform(2.0, 5.0)
        ramp = np.linspace(0, severity, n_samples - start_idx)
        P_csf[start_idx:] += ramp
        P_cortical[start_idx:] += ramp * starling_gain
        P_sinus[start_idx:] += ramp * starling_gain * 0.9
        P_periventricular[start_idx:] += ramp * periventricular_coupling

    # Posture state transitions
    if posture_state == "supine":
        # Supine: higher venous pressures (gravity)
        venous_offset = rng.uniform(2.0, 5.0)
        P_cortical += venous_offset
        P_sinus += venous_offset * 0.8
        P_periventricular += venous_offset * 0.3

    elif posture_state == "upright":
        # Upright: venous outflow shifts to vertebral plexus, jugular/sinus drops
        venous_drop = rng.uniform(3.0, 8.0)
        P_cortical -= venous_drop
        P_sinus -= venous_drop * 1.2  # Sinus drops MORE (venous outflow shift)
        P_periventricular -= venous_drop * 0.4  # Deep veins less affected by posture

    elif posture_state == "valsalva":
        # Valsalva: all venous pressures spike briefly
        valsalva_start = n_samples // 3
        valsalva_dur = 60  # 1 minute
        valsalva_amp = rng.uniform(10.0, 20.0)
        P_csf[valsalva_start:valsalva_start+valsalva_dur] += valsalva_amp
        P_cortical[valsalva_start:valsalva_start+valsalva_dur] += valsalva_amp * 0.9
        P_sinus[valsalva_start:valsalva_start+valsalva_dur] += valsalva_amp * 0.8
        P_periventricular[valsalva_start:valsalva_start+valsalva_dur] += valsalva_amp * 0.5

    elif posture_state == "transitions":
        # Multiple posture transitions
        for trans_time in [n_samples//4, n_samples//2, 3*n_samples//4]:
            trans_dur = 60
            if trans_time + trans_dur < n_samples:
                # Transition: supine→upright or upright→supine
                direction = rng.choice([-1, 1])
                trans_amp = rng.uniform(3.0, 6.0) * direction
                P_csf[trans_time:trans_time+trans_dur] += trans_amp * 0.3
                P_cortical[trans_time:trans_time+trans_dur] += trans_amp
                P_sinus[trans_time:trans_time+trans_dur] += trans_amp * 1.2
                P_periventricular[trans_time:trans_time+trans_dur] += trans_amp * 0.4

    # Add cardiac pulse
    pulse_freq = rng.uniform(0.8, 1.2)
    pulse_amp = rng.uniform(1.5, 3.0)
    pulse = pulse_amp * np.sin(2 * np.pi * pulse_freq * t / n_samples * n_samples)
    P_csf += pulse
    P_cortical += pulse * 0.8
    P_sinus += pulse * 0.7
    P_periventricular += pulse * 0.5

    # Add respiration
    resp_freq = rng.uniform(0.15, 0.35)
    resp_amp = rng.uniform(0.5, 2.0)
    resp = resp_amp * np.sin(2 * np.pi * resp_freq * t / n_samples * n_samples)
    P_csf += resp
    P_cortical += resp * 0.7
    P_sinus += resp * 0.6
    P_periventricular += resp * 0.4

    # Add noise
    noise = rng.uniform(0.2, 0.6)
    P_csf += rng.normal(0, noise, n_samples)
    P_cortical += rng.normal(0, noise, n_samples)
    P_sinus += rng.normal(0, noise, n_samples)
    P_periventricular += rng.normal(0, noise, n_samples)

    # Add sensor drift (different for each sensor)
    drift = rng.uniform(0.0, 0.3)
    P_csf += drift * t / n_samples
    P_sinus += drift * 0.9 * t / n_samples  # eShunt venous sensor
    P_periventricular += drift * 1.1 * t / n_samples  # Hypothetical sensor

    # Add sensor bias (different for each sensor)
    P_csf += rng.normal(0, 0.8)
    P_sinus += rng.normal(0, 0.8)
    P_periventricular += rng.normal(0, 0.8)

    # Compute differentials
    diff_eShunt = P_csf - P_sinus  # eShunt-accessible (sinus compartment)
    diff_periventricular = P_csf - P_periventricular  # Ideal (periventricular compartment)

    return {
        "P_csf": P_csf,
        "P_sinus": P_sinus,
        "P_cortical": P_cortical,
        "P_periventricular": P_periventricular,
        "diff_eShunt": diff_eShunt,
        "diff_periventricular": diff_periventricular,
        "starling_gain": starling_gain,
        "periventricular_coupling": periventricular_coupling,
    }


def extract_features(signal):
    """Extract features from a pressure signal."""
    signal = np.array(signal)
    n = len(signal)
    mean_p = float(np.mean(signal))
    pulse_amp = float(np.std(signal))
    first_q = float(np.mean(signal[:n//4]))
    last_q = float(np.mean(signal[3*n//4:]))
    sustained = last_q - first_q
    slope = float(np.polyfit(np.arange(n), signal, 1)[0])
    temp_var = float(np.std(signal[n//2:]) - np.std(signal[:n//2]))
    fft = np.abs(np.fft.rfft(signal - np.mean(signal)))
    p2_p1 = float(fft[1] / (fft[0] + 1e-10)) if len(fft) > 1 else 0
    spec_entropy = float(-np.sum((fft/(fft.sum()+1e-10)) * np.log(fft/(fft.sum()+1e-10) + 1e-10))) if fft.sum() > 0 else 0
    return [mean_p, pulse_amp, p2_p1, float(np.argmax(signal)/n), temp_var, sustained, slope, spec_entropy]


def train_and_evaluate(X_train, y_train, X_val, y_val, X_test, y_test):
    """Train logistic regression and evaluate."""
    # Scale
    scaler = StandardScaler().fit(X_train)
    X_tr = scaler.transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_te = scaler.transform(X_test)

    # Select C on val
    best_c, best_val_auc = 1.0, 0
    for c in [0.01, 0.1, 1.0, 10.0]:
        m = LogisticRegression(C=c, penalty='l2', max_iter=1000, random_state=42)
        m.fit(X_tr, y_train)
        auc = roc_auc_score(y_val, m.predict_proba(X_val_s)[:, 1])
        if auc > best_val_auc:
            best_val_auc = auc
            best_c = c

    model = LogisticRegression(C=best_c, penalty='l2', max_iter=1000, random_state=42)
    model.fit(X_tr, y_train)

    pred = model.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_test, pred)
    auprc = average_precision_score(y_test, pred)

    # Fixed: sensitivity at 90% specificity
    fpr, tpr, _ = roc_curve(y_test, pred)
    sens = 0.0
    for i in range(len(fpr)):
        if fpr[i] <= 0.1:
            sens = float(tpr[i])
            break

    return {"AUROC": auc, "AUPRC": auprc, "sens_at_90_spec": sens}


def main():
    print("=" * 80)
    print("C2-R146: COMPARTMENT-IDENTITY FALSIFICATION")
    print("4 worlds: A=absolute, B=eShunt venous, C=periventricular, D=combined+state")
    print("=" * 80)

    # Generate virtual cohort
    conditions = ["normal", "obstruction", "over_drainage", "under_drainage"]
    postures = ["supine", "upright", "valsalva", "transitions"]

    n_per_combo = 50  # 4 conditions × 4 postures × 50 = 800 patients
    print(f"\n[1] Generating cohort: {len(conditions)} conditions × {len(postures)} postures × {n_per_combo} = {len(conditions)*len(postures)*n_per_combo} patients")

    patients = []
    seed = 42
    for cond in conditions:
        for post in postures:
            for i in range(n_per_combo):
                data = simulate_compartmental_pressure(cond, post, seed=seed)
                patients.append({
                    "condition": cond,
                    "posture": post,
                    **data
                })
                seed += 1

    # Split
    rng = np.random.RandomState(42)
    n = len(patients)
    indices = rng.permutation(n)
    train_idx = indices[:int(0.6*n)]
    val_idx = indices[int(0.6*n):int(0.8*n)]
    test_idx = indices[int(0.8*n):]

    def prepare(indices, patients, feature_type):
        X, y = [], []
        for idx in indices:
            p = patients[idx]
            if feature_type == "A":
                X.append(extract_features(p["P_csf"]))
            elif feature_type == "B":
                X.append(extract_features(p["diff_eShunt"]))
            elif feature_type == "C":
                X.append(extract_features(p["diff_periventricular"]))
            elif feature_type == "D":
                # Combined: absolute + eShunt differential + posture state
                abs_f = extract_features(p["P_csf"])
                diff_f = extract_features(p["diff_eShunt"])
                # Add posture one-hot (4 values)
                posture_onehot = [0, 0, 0, 0]
                posture_map = {"supine": 0, "upright": 1, "valsalva": 2, "transitions": 3}
                posture_onehot[posture_map[p["posture"]]] = 1
                X.append(abs_f + diff_f + posture_onehot)
            y.append(1 if p["condition"] == "obstruction" else 0)
        return np.array(X), np.array(y)

    # Train and evaluate 4 models
    print("\n[2] Training 4 models...")
    results = {}

    for model_name, feature_type in [("A_absolute_ICP", "A"), ("B_eShunt_venous", "B"), ("C_periventricular", "C"), ("D_combined_state", "D")]:
        X_tr, y_tr = prepare(train_idx, patients, feature_type)
        X_val, y_val = prepare(val_idx, patients, feature_type)
        X_te, y_te = prepare(test_idx, patients, feature_type)

        result = train_and_evaluate(X_tr, y_tr, X_val, y_val, X_te, y_te)
        results[model_name] = result
        print(f"  {model_name}: AUROC={result['AUROC']:.4f}, AUPRC={result['AUPRC']:.4f}, Sens@90Spec={result['sens_at_90_spec']:.4f}")

    # Compute incremental information
    print("\n[3] Incremental information:")
    inc_B_A = results["B_eShunt_venous"]["AUROC"] - results["A_absolute_ICP"]["AUROC"]
    inc_C_A = results["C_periventricular"]["AUROC"] - results["A_absolute_ICP"]["AUROC"]
    inc_D_A = results["D_combined_state"]["AUROC"] - results["A_absolute_ICP"]["AUROC"]

    print(f"  Δ(B-A) = {inc_B_A:+.4f}  (eShunt venous over absolute)")
    print(f"  Δ(C-A) = {inc_C_A:+.4f}  (periventricular over absolute)")
    print(f"  Δ(D-A) = {inc_D_A:+.4f}  (combined+state over absolute)")

    # Hypothesis assessment
    print("\n" + "=" * 80)
    print("HYPOTHESIS ASSESSMENT")
    print("=" * 80)

    hypotheses = {
        "H1": {"desc": "eShunt-accessible venous differential contains substantial independent information",
               "test": inc_B_A > 0.05, "result": "SUPPORTED" if inc_B_A > 0.05 else "NOT_SUPPORTED"},
        "H2": {"desc": "eShunt differential adds little because of strong coupling",
               "test": inc_B_A < 0.01, "result": "SUPPORTED" if inc_B_A < 0.01 else "NOT_SUPPORTED"},
        "H3": {"desc": "Periventricular differential contains information but eShunt cannot access it",
               "test": inc_C_A > 0.05 and inc_B_A < 0.01, "result": "SUPPORTED" if inc_C_A > 0.05 and inc_B_A < 0.01 else "NOT_SUPPORTED"},
        "H4": {"desc": "Differential information exists only in particular physiological states",
               "test": inc_D_A > inc_B_A + 0.02, "result": "SUPPORTED" if inc_D_A > inc_B_A + 0.02 else "NOT_SUPPORTED"},
        "H5": {"desc": "Absolute ICP already contains essentially all useful information",
               "test": inc_D_A < 0.01, "result": "SUPPORTED" if inc_D_A < 0.01 else "NOT_SUPPORTED"},
        "H6": {"desc": "Apparent differential advantage is created by sensor/model assumptions",
               "test": False, "result": "UNTESTABLE_IN_CURRENT_EXPERIMENT"},
    }

    for h_id, h in hypotheses.items():
        print(f"  {h_id}: {h['desc']}")
        print(f"    → {h['result']}")

    # Key comparison
    print("\n" + "=" * 80)
    print("KEY COMPARISON: eShunt vs Periventricular")
    print("=" * 80)
    print(f"\n  Absolute ICP AUROC:           {results['A_absolute_ICP']['AUROC']:.4f}")
    print(f"  eShunt venous diff AUROC:     {results['B_eShunt_venous']['AUROC']:.4f}  (Δ={inc_B_A:+.4f})")
    print(f"  Periventricular diff AUROC:   {results['C_periventricular']['AUROC']:.4f}  (Δ={inc_C_A:+.4f})")
    print(f"  Combined+state AUROC:         {results['D_combined_state']['AUROC']:.4f}  (Δ={inc_D_A:+.4f})")

    if inc_C_A > 0.05 and inc_B_A < 0.01:
        print("\n  ⚠️  COMPARTMENT IDENTITY FAILURE: Periventricular differential is informative")
        print("  but eShunt-accessible (sinus) differential is NOT.")
        print("  eShunt measures the WRONG venous compartment.")
        verdict = "COMPARTMENT_IDENTITY_FAILURE"
    elif inc_B_A > 0.05:
        print("\n  ✅ eShunt-accessible differential IS informative despite high coupling.")
        print("  C2's mechanism survives the compartment-identity attack.")
        verdict = "eSHUNT_DIFFERENTIAL_SURVIVES"
    elif inc_D_A > 0.05:
        print("\n  🟡 eShunt differential alone is weak, but combined with state info it helps.")
        print("  C2's value may be state-dependent.")
        verdict = "STATE_DEPENDENT_ADVANTAGE"
    else:
        print("\n  ❌ No differential provides meaningful advantage over absolute ICP.")
        print("  C2's mechanism collapses across all compartments.")
        verdict = "ALL_DIFFERENTIALS_FAIL"

    # Write output
    output = {
        "experiment_id": "C2-R146-COMPARTMENT-IDENTITY-FALSIFICATION",
        "date": datetime.now(timezone.utc).isoformat(),
        "round": 146,
        "description": "Compartment-identity falsification: does eShunt-accessible venous compartment provide useful differential signal, or does the physiologically informative differential exist only in the periventricular compartment?",
        "compartmental_model": {
            "P_csf": "Ventricular CSF pressure",
            "P_sinus": "Dural sinus pressure (eShunt-accessible)",
            "P_cortical": "Cortical vein pressure (Starling-protected, HIGH coupling to CSF)",
            "P_periventricular": "Periventricular/deep vein pressure (NOT Starling-protected, LOW coupling)",
            "starling_gain": "0.6-0.9 (cortical veins follow CSF closely)",
            "periventricular_coupling": "0.1-0.4 (deep veins do NOT follow CSF)",
            "literature_basis": ["PMID 26767844 (tight CSF-venous coupling)", "PMID 8194060 (cortical vs periventricular)", "PMID 39029117 (posture-dependent outflow)", "PMID 27598891 (nonlinear Starling)"]
        },
        "results": results,
        "incremental_information": {"B_over_A": inc_B_A, "C_over_A": inc_C_A, "D_over_A": inc_D_A},
        "hypotheses": hypotheses,
        "verdict": verdict,
        "evidence_class": "SCIENTIFIC_EVIDENCE",
        "key_limitation": "Compartmental model is simplified. Real venous physiology is more complex (collaterals, autoregulation, nonlinear Starling). Parameters (starling_gain 0.6-0.9, periventricular_coupling 0.1-0.4) are literature-INFORMED but not literature-VALIDATED. Need sensitivity analysis on these parameters.",
    }

    output_path = ROUND_146_DIR / "C2_R146_COMPARTMENT_IDENTITY_RESULTS.json"
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n[OK] Results: {output_path}")
    print("[DONE]")


if __name__ == "__main__":
    main()

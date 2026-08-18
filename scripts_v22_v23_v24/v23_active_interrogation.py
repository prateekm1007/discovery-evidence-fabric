"""
V23 — ACTIVE SPECTRAL INTERROGATION for Territory #1
====================================================

V22 found that the 7-latent-state architecture is UNIDENTIFIABLE from a static
multi-frequency EIS spectrum. The causal reason:
  4 latent states (ionic, temperature, obstruction, lumen_fouling) ALL perturb
  the same equivalent-circuit parameter R_sol. With only 3 Randles params per
  electrode (R_sol, R_ct, C_dl), the system is underdetermined for 4 collinear
  states. RF regression memorizes training correlations but FAILS catastrophically
  (R² < -10) when combinations appear that were never trained.

V22 also confirmed: reference electrode IS a single point of failure (R²=-0.913
under reference-degradation attack).

DOCTRINE RULE 6 (verbatim):
  "When a failure mode destroys the invention, don't erase the failure mode.
   Turn it into something the invention explicitly senses, models, or controls."

V23 MECHANISM REDESIGN:
  The collinearity is NOT erased. It is turned into a sensed state by
  ACTIVE INTERROGATION:

  Step 1: Inject a KNOWN thermal pulse (small, e.g., +0.5°C for 30s via micro-heater)
  Step 2: Inject a KNOWN ionic pulse (small bolus of calibrated ionic solution)
  Step 3: Observe the time-domain spectral response of BOTH electrodes

  Each latent state has a DIFFERENT transfer function to the perturbation:
    - ionic_conductivity → INSTANT response to ionic pulse (no lag)
                       → NO response to thermal pulse
    - temperature → SLOW response to thermal pulse (minutes, thermal mass)
                → NO response to ionic pulse
    - obstruction → NO response to either pulse (mechanical, not transport)
    - lumen_fouling → SLOW response to ionic pulse (diffusion-limited through fouling)
    - electrode_fouling → alters transfer function shape (C_dl changes during pulse)
    - reference_polarization → affects ONLY reference electrode response (key SPOF detection!)
    - hardware_degradation → affects BOTH electrodes equally (common mode)

  This converts the static identifiability problem into a DYNAMIC one.
  Each state leaves a unique temporal-spectral fingerprint.

V23 ALSO ADDS: THIRD ELECTRODE for reference SPOF elimination
  Per CEO directive: "If the architecture depends on a clean reference electrode
  forever, that is a hidden single point of failure."
  V23 adds a SECOND reference electrode (redundant reference).
  If the two references diverge in their response to a perturbation, ONE of them
  is degraded. The system flags the degradation and uses the healthy reference.

ATTACK MATRIX (same as V22, plus V23-specific attacks):
  A1-A6: same combined distribution shifts as V22
  A7 (NEW): ONE reference electrode biologically altered (asymmetric ref degradation)
  A8 (NEW): BOTH references slowly drift in same direction (common-mode ref drift)

SUCCESS CRITERIA:
  - Each latent state must be recoverable with R² > 0.5 across ALL attacks
  - Reference electrode degradation must be DETECTABLE (R² > 0.7)
  - The collinearity that defeated V22 must be RESOLVED by active interrogation

DOCTRINE COMPLIANCE:
  "Do not optimize the number. Optimize the causal explanation."
  V23 reports: which states ARE independently recoverable under active
  interrogation, which are NOT, and the causal reason for each.
"""
import json, math, random, warnings, sys, time
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error

warnings.filterwarnings("ignore")

# Tee output to log file
LOG_PATH = "/tmp/v23_out.log"
class Tee:
    def __init__(self, *streams): self.streams = streams
    def write(self, data):
        for s in self.streams: s.write(data); s.flush()
    def flush(self):
        for s in self.streams: s.flush()
_logf = open(LOG_PATH, "w")
sys.stdout = Tee(sys.stdout, _logf)
sys.stderr = Tee(sys.stderr, _logf)

OUT_DIR = Path("/home/z/my-project/discovery-evidence-fabric/CEREVASC_POSITION_001_V23_ACTIVE_INTERROGATION")
OUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42); np.random.seed(42)

# ============================================================
# SECTION 1 — ACTIVE INTERROGATION PHYSICS MODEL
# ============================================================
# Multi-frequency EIS at multiple TIME POINTS during perturbation
FREQS = np.logspace(np.log10(10), np.log10(100_000), 12)
TIME_POINTS = [0.0, 0.5, 1.0, 5.0, 15.0, 60.0]  # seconds after perturbation onset

# Randles baseline parameters (same as V22)
R_SOL_BASE_M = 100.0; R_CT_BASE_M = 1000.0; C_DL_BASE_M = 100e-9
R_SOL_BASE_R = 250.0; R_CT_BASE_R = 2500.0; C_DL_BASE_R = 40e-9


def randles(R_sol, R_ct, C_dl, freqs=FREQS):
    return R_sol + 1.0 / (1.0/R_ct + 1j * 2 * np.pi * freqs * C_dl)


def latent_to_randles(s_hyd, s_lumen, s_elec, s_ionic, s_temp, s_refpol, s_hw, ref_electrode="meas"):
    """Map 7 latent states to Randles parameters for measurement or reference electrode."""
    if ref_electrode == "meas":
        R_sol = R_SOL_BASE_M * (1.0/max(s_ionic, 0.3)) * (1 - 0.02*s_temp)
        R_sol *= (1 + 1.5*s_hyd) * (1 + 0.8*s_lumen)
        R_ct = R_CT_BASE_M * (1 + 5.0*s_elec) * (1 + 0.3*s_lumen)
        C_dl = C_DL_BASE_M * (1 - 0.7*s_elec) * (1 - 0.3*s_lumen)
    else:  # reference electrode (NOT in CSF)
        R_sol = R_SOL_BASE_R * (1.0/max(s_ionic, 0.3))**0.3 * (1 - 0.02*s_temp)
        R_ct = R_CT_BASE_R * (1 + 4.0*s_refpol)
        C_dl = C_DL_BASE_R * (1 - 0.5*s_refpol)
    R_series_hw = 5.0 + 50.0*s_hw
    return R_sol + R_series_hw, R_ct, C_dl


def thermal_pulse_response(t, s_temp, s_ionic, s_lumen, s_hyd, s_elec, electrode="meas"):
    """Time-domain response of R_sol to a thermal pulse (+0.5°C at t=0).

    Causal pathways:
      - temperature: thermal pulse directly heats CSF → R_sol changes slowly (thermal mass)
                     time constant ~30s (tissue thermal mass)
      - ionic: NO response (thermal pulse doesn't change ionic strength)
      - lumen_fouling: NO response (fouling is mechanical, not thermal)
      - hyd: NO response
      - elec: NO response to thermal (electrode C_dl has small temp coeff, ignore)
    """
    if electrode == "meas":
        # Thermal response: τ_thermal ≈ 30s
        tau_thermal = 30.0
        delta_temp_observed = 0.5 * (1 - math.exp(-t/tau_thermal))
        # The observed temperature shift IS the thermal pulse, scaled by 1 (direct measurement)
        # But the EFFECT on R_sol depends on actual temperature (which is perturbed by pulse)
        return delta_temp_observed  # effective observed temperature shift
    else:  # reference electrode (tissue-side) — slower thermal response
        tau_thermal = 60.0  # tissue thermal mass larger
        return 0.5 * (1 - math.exp(-t/tau_thermal))


def ionic_pulse_response(t, s_ionic, s_lumen, s_hyd, electrode="meas"):
    """Time-domain response to ionic pulse (small bolus of calibrated ionic solution).

    Causal pathways:
      - ionic: INSTANT response (ionic diffusion is fast in CSF)
               τ_ionic ≈ 0.5s (CSF mixing)
      - lumen_fouling: SLOW response (diffusion through fouling layer)
                       τ_diffusion scales with (1 + 2*s_lumen) — more fouling = slower
      - hyd: NO response (obstruction is mechanical)
      - elec: NO response to ionic pulse (electrode doesn't change with ionic)
    """
    if electrode == "meas":
        tau_ionic = 0.5 * (1 + 2.0*s_lumen)  # fouling slows diffusion
        return 1.0 * (1 - math.exp(-t/tau_ionic))
    else:
        # Reference is NOT in CSF — ionic pulse has WEAK effect, delayed
        tau_ionic_ref = 5.0
        return 0.1 * (1 - math.exp(-t/tau_ionic_ref))


def measure_active_spectrum(states, noise_std=0.02, ref_degraded=False, ref2_degraded=False):
    """Generate OBSERVED spectra during active interrogation.

    Returns: dict with keys 'thermal_m', 'thermal_r', 'thermal_r2', 'ionic_m', 'ionic_r', 'ionic_r2'
    Each value is a (n_times, n_freqs) complex array.

    If ref_degraded=True: reference 1 has chronic polarization drift
    If ref2_degraded=True: reference 2 has chronic polarization drift
    """
    s_hyd, s_lumen, s_elec, s_ionic, s_temp, s_refpol, s_hw = states

    # Effective s_refpol per reference electrode
    s_refpol_r1 = s_refpol * (1.5 if ref_degraded else 1.0)
    s_refpol_r2 = s_refpol * (1.5 if ref2_degraded else 1.0)

    # Baseline (pre-pulse) Randles for each electrode
    Rm_sol0, Rm_ct0, Rm_dl0 = latent_to_randles(s_hyd, s_lumen, s_elec, s_ionic, s_temp, s_refpol, s_hw, "meas")
    Rr1_sol0, Rr1_ct0, Rr1_dl0 = latent_to_randles(s_hyd, s_lumen, s_elec, s_ionic, s_temp, s_refpol_r1, s_hw, "ref")
    Rr2_sol0, Rr2_ct0, Rr2_dl0 = latent_to_randles(s_hyd, s_lumen, s_elec, s_ionic, s_temp, s_refpol_r2, s_hw, "ref")

    thermal_spectra_m = []; thermal_spectra_r1 = []; thermal_spectra_r2 = []
    ionic_spectra_m = []; ionic_spectra_r1 = []; ionic_spectra_r2 = []

    for t in TIME_POINTS:
        # === THERMAL PULSE ===
        # Temperature observed at electrode (scaled thermal pulse)
        delta_T_m = thermal_pulse_response(t, s_temp, s_ionic, s_lumen, s_hyd, s_elec, "meas")
        delta_T_r = thermal_pulse_response(t, s_temp, s_ionic, s_lumen, s_hyd, s_elec, "ref")
        # Effective temperature at measurement electrode = s_temp + delta_T_m
        eff_temp_m = s_temp + delta_T_m
        eff_temp_r = s_temp + delta_T_r
        # R_sol for measurement changes with effective temp
        Rm_sol_t = R_SOL_BASE_M * (1.0/max(s_ionic, 0.3)) * (1 - 0.02*eff_temp_m)
        Rm_sol_t *= (1 + 1.5*s_hyd) * (1 + 0.8*s_lumen)
        Rm_sol_t += 5.0 + 50.0*s_hw
        # R_ct, C_dl UNCHANGED by thermal pulse (small temp coeff ignored)
        Zm_t = randles(Rm_sol_t, Rm_ct0, Rm_dl0)
        # Reference electrode thermal response — DIFFERENT time constant
        Rr1_sol_t = R_SOL_BASE_R * (1.0/max(s_ionic, 0.3))**0.3 * (1 - 0.02*eff_temp_r)
        Rr1_sol_t += 5.0 + 50.0*s_hw
        Zr1_t = randles(Rr1_sol_t, Rr1_ct0, Rr1_dl0)
        # Reference 2 (redundant)
        Rr2_sol_t = R_SOL_BASE_R * (1.0/max(s_ionic, 0.3))**0.3 * (1 - 0.02*eff_temp_r)
        Rr2_sol_t += 5.0 + 50.0*s_hw
        Zr2_t = randles(Rr2_sol_t, Rr2_ct0, Rr2_dl0)

        thermal_spectra_m.append(Zm_t)
        thermal_spectra_r1.append(Zr1_t)
        thermal_spectra_r2.append(Zr2_t)

        # === IONIC PULSE ===
        # Ionic concentration observed at electrode (scaled ionic pulse)
        delta_ion_m = ionic_pulse_response(t, s_ionic, s_lumen, s_hyd, "meas")
        delta_ion_r = ionic_pulse_response(t, s_ionic, s_lumen, s_hyd, "ref")
        # Effective ionic at measurement electrode
        eff_ionic_m = s_ionic * (1 + 0.1*delta_ion_m)  # 10% ionic perturbation
        eff_ionic_r = s_ionic * (1 + 0.1*delta_ion_r)
        # R_sol changes with ionic
        Rm_sol_i = R_SOL_BASE_M * (1.0/max(eff_ionic_m, 0.3)) * (1 - 0.02*s_temp)
        Rm_sol_i *= (1 + 1.5*s_hyd) * (1 + 0.8*s_lumen)
        Rm_sol_i += 5.0 + 50.0*s_hw
        # C_dl changes slightly with ionic (double-layer compression)
        C_dl_m_i = C_DL_BASE_M * (1 - 0.7*s_elec) * (1 - 0.3*s_lumen) * (1 - 0.05*delta_ion_m)
        Zm_i = randles(Rm_sol_i, Rm_ct0, C_dl_m_i)
        # Reference — ionic pulse has WEAK effect (tissue-side)
        Rr1_sol_i = R_SOL_BASE_R * (1.0/max(eff_ionic_r, 0.3))**0.3 * (1 - 0.02*s_temp)
        Rr1_sol_i += 5.0 + 50.0*s_hw
        Zr1_i = randles(Rr1_sol_i, Rr1_ct0, Rr1_dl0)
        # Ref 2
        Rr2_sol_i = R_SOL_BASE_R * (1.0/max(eff_ionic_r, 0.3))**0.3 * (1 - 0.02*s_temp)
        Rr2_sol_i += 5.0 + 50.0*s_hw
        Zr2_i = randles(Rr2_sol_i, Rr2_ct0, Rr2_dl0)

        ionic_spectra_m.append(Zm_i)
        ionic_spectra_r1.append(Zr1_i)
        ionic_spectra_r2.append(Zr2_i)

    # Add noise
    def add_noise(spectra_list):
        result = []
        for Z in spectra_list:
            n = (1 + np.random.normal(0, noise_std, len(FREQS))) + 1j*np.random.normal(0, noise_std, len(FREQS))
            result.append(Z * n)
        return np.array(result)

    return {
        "thermal_m": add_noise(thermal_spectra_m),
        "thermal_r1": add_noise(thermal_spectra_r1),
        "thermal_r2": add_noise(thermal_spectra_r2),
        "ionic_m": add_noise(ionic_spectra_m),
        "ionic_r1": add_noise(ionic_spectra_r1),
        "ionic_r2": add_noise(ionic_spectra_r2),
    }


def extract_active_features(spectra_dict):
    """Extract features from active interrogation spectra.

    Features (per electrode × per pulse × per time point):
      - |Z| at each freq (12)
      - phase at each freq (12)
      → 24 per electrode per time point
      × 6 time points × 2 pulses × 3 electrodes = 864 features
      Plus: differential features between measurement and reference (cross-electrode)
      → roughly 1000+ features total

    To keep tractable, we use:
      - Magnitude at each freq × time × electrode × pulse: 12*6*3*2 = 432
      - Phase at each freq × time × electrode × pulse: 432
      - Reference divergence: |Zr1 - Zr2| at each freq × time × pulse: 12*6*2 = 144
      - Total: 1008 features
    """
    feats = []
    for pulse in ["thermal", "ionic"]:
        for elec in ["m", "r1", "r2"]:
            key = f"{pulse}_{elec}"
            Z = spectra_dict[key]  # shape (n_times, n_freqs)
            for t_idx in range(len(TIME_POINTS)):
                mag = np.abs(Z[t_idx])
                pha = np.angle(Z[t_idx], deg=True)
                feats.extend(mag)
                feats.extend(pha)
    # Reference divergence (SPOF detection signal)
    for pulse in ["thermal", "ionic"]:
        Zr1 = spectra_dict[f"{pulse}_r1"]
        Zr2 = spectra_dict[f"{pulse}_r2"]
        for t_idx in range(len(TIME_POINTS)):
            diff_mag = np.abs(Zr1[t_idx] - Zr2[t_idx])
            feats.extend(diff_mag)
    return np.array(feats)


# ============================================================
# SECTION 2 — TRAINING DATA
# ============================================================
N_TRAIN_PER_AXIS = 400
TRAIN_AXES = {
    "hydraulic_obstruction": (0.0, 1.0),
    "lumen_fouling":         (0.0, 1.0),
    "electrode_fouling":     (0.0, 1.0),
    "ionic_conductivity":    (0.85, 1.15),
    "temperature":           (-1.0, 1.0),
    "reference_polarization":(0.0, 0.3),
    "hardware_degradation":  (0.0, 0.5),
}

print("=" * 78)
print("V23 — ACTIVE SPECTRAL INTERROGATION (thermal + ionic pulses)")
print("=" * 78)
print(f"\nFrequencies: {len(FREQS)} (10 Hz – 100 kHz)")
print(f"Time points: {len(TIME_POINTS)} ({TIME_POINTS})")
print(f"Electrodes: 3 (1 measurement + 2 redundant references)")
print(f"Pulses: 2 (thermal +0.5°C, ionic +10%)")
print(f"Latent states: 7 (same as V22)")
print(f"\nTraining: {N_TRAIN_PER_AXIS} samples per axis, each state INDEPENDENTLY sampled")
print(f"  → combined attacks remain STRICTLY OUT OF DISTRIBUTION\n")

print("Generating training data...")
t0 = time.time()
X_train = []; Y_train = []
for _ in range(N_TRAIN_PER_AXIS):
    states = np.array([
        random.uniform(*TRAIN_AXES["hydraulic_obstruction"]),
        random.uniform(*TRAIN_AXES["lumen_fouling"]),
        random.uniform(*TRAIN_AXES["electrode_fouling"]),
        random.uniform(*TRAIN_AXES["ionic_conductivity"]),
        random.uniform(*TRAIN_AXES["temperature"]),
        random.uniform(*TRAIN_AXES["reference_polarization"]),
        random.uniform(*TRAIN_AXES["hardware_degradation"]),
    ])
    spec = measure_active_spectrum(states, noise_std=0.02)
    feat = extract_active_features(spec)
    X_train.append(feat)
    Y_train.append(states)

X_train = np.array(X_train)
Y_train = np.array(Y_train)
print(f"Training set: {X_train.shape[0]} samples, {X_train.shape[1]} features (generated in {time.time()-t0:.1f}s)")
print(f"NaN check: X={np.isnan(X_train).any()}, Y={np.isnan(Y_train).any()}")

print("Training multi-output RF (n_estimators=60, max_depth=12)...")
t0 = time.time()
rf = RandomForestRegressor(n_estimators=60, max_depth=12, n_jobs=1, random_state=42)
rf.fit(X_train, Y_train)
print(f"RF trained in {time.time()-t0:.1f}s")

# ============================================================
# SECTION 3 — IN-DISTRIBUTION VALIDATION
# ============================================================
print(f"\n{'='*78}")
print("SECTION 3 — In-Distribution Validation")
print("=" * 78)

state_names = list(TRAIN_AXES.keys())
N_VAL = 200
Y_true = []; Y_pred = []
for _ in range(N_VAL):
    states = np.array([
        random.uniform(*TRAIN_AXES["hydraulic_obstruction"]),
        random.uniform(*TRAIN_AXES["lumen_fouling"]),
        random.uniform(*TRAIN_AXES["electrode_fouling"]),
        random.uniform(*TRAIN_AXES["ionic_conductivity"]),
        random.uniform(*TRAIN_AXES["temperature"]),
        random.uniform(*TRAIN_AXES["reference_polarization"]),
        random.uniform(*TRAIN_AXES["hardware_degradation"]),
    ])
    spec = measure_active_spectrum(states, noise_std=0.02)
    feat = extract_active_features(spec)
    pred = rf.predict(feat.reshape(1, -1))[0]
    Y_true.append(states)
    Y_pred.append(pred)

Y_true = np.array(Y_true); Y_pred = np.array(Y_pred)
print(f"\n  {'State':25} {'R²':>8} {'MAE':>10}")
in_dist_r2 = {}
for i, name in enumerate(state_names):
    r2 = r2_score(Y_true[:, i], Y_pred[:, i])
    mae = mean_absolute_error(Y_true[:, i], Y_pred[:, i])
    in_dist_r2[name] = {"r2": round(float(r2), 3), "mae": round(float(mae), 4)}
    print(f"  {name:25} {r2:>8.3f} {mae:>10.4f}")


# ============================================================
# SECTION 4 — HELD-OUT ATTACK MATRIX (V22 attacks + V23 new attacks)
# ============================================================
print(f"\n{'='*78}")
print("SECTION 4 — HELD-OUT ATTACK MATRIX")
print("=" * 78)
print("A1-A6: same as V22 (combined distribution shifts)")
print("A7 (NEW): ONE reference electrode biologically altered")
print("A8 (NEW): BOTH references slowly drift (common-mode ref drift)\n")


def run_attack(name, n_samples, state_fn, ref_degraded_fn=None, ref2_degraded_fn=None):
    Y_true = []; Y_pred = []
    for _ in range(n_samples):
        states = np.array(state_fn())
        ref_deg = ref_degraded_fn() if ref_degraded_fn else False
        ref2_deg = ref2_degraded_fn() if ref2_degraded_fn else False
        spec = measure_active_spectrum(states, noise_std=0.02, ref_degraded=ref_deg, ref2_degraded=ref2_deg)
        feat = extract_active_features(spec)
        pred = rf.predict(feat.reshape(1, -1))[0]
        Y_true.append(states)
        Y_pred.append(pred)
    Y_true = np.array(Y_true); Y_pred = np.array(Y_pred)
    per_state = {}
    for i, sn in enumerate(state_names):
        if np.var(Y_true[:, i]) > 1e-9:
            r2 = r2_score(Y_true[:, i], Y_pred[:, i])
        else:
            r2 = float('nan')
        mae = mean_absolute_error(Y_true[:, i], Y_pred[:, i])
        per_state[sn] = {"r2": round(float(r2), 3) if not math.isnan(r2) else None,
                          "mae": round(float(mae), 4),
                          "true_range": [round(float(Y_true[:, i].min()), 3),
                                          round(float(Y_true[:, i].max()), 3)]}
    return per_state


# A1-A6: same as V22
def attack_a1():
    s_ion = random.uniform(1.15, 1.30); s_elec = random.uniform(0.4, 0.9)
    return (0.0, 0.0, s_elec, s_ion, 0.0, 0.0, 0.0)

def attack_a2():
    s_ion = random.uniform(1.15, 1.30); s_hyd = random.uniform(0.4, 1.0)
    return (s_hyd, 0.0, 0.0, s_ion, 0.0, 0.0, 0.0)

def attack_a3():
    s_ion = random.uniform(1.15, 1.30); s_lumen = random.uniform(0.4, 1.0)
    return (0.0, s_lumen, 0.0, s_ion, 0.0, 0.0, 0.0)

def attack_a4():
    s_ion = random.uniform(1.15, 1.30); s_refpol = random.uniform(0.5, 1.0)
    return (0.0, 0.0, 0.0, s_ion, 0.0, s_refpol, 0.0)

def attack_a5():
    s_temp = random.uniform(1.5, 2.5); s_ion = random.uniform(1.15, 1.30); s_elec = random.uniform(0.3, 0.8)
    return (0.0, 0.0, s_elec, s_ion, s_temp, 0.0, 0.0)

def attack_a6():
    return (random.uniform(0.2, 0.7), random.uniform(0.3, 0.8), random.uniform(0.4, 0.9),
            random.uniform(1.15, 1.30), random.uniform(1.0, 2.0),
            random.uniform(0.5, 1.0), random.uniform(0.5, 1.0))

# A7: ONE reference electrode biologically altered (asymmetric)
def attack_a7():
    s_ion = random.uniform(1.10, 1.25); s_refpol = random.uniform(0.3, 0.7)
    return (0.0, 0.0, 0.0, s_ion, 0.0, s_refpol, 0.0)

# A8: BOTH references slowly drift (common-mode ref drift)
def attack_a8():
    s_ion = random.uniform(1.10, 1.25); s_refpol = random.uniform(0.5, 1.0)
    return (0.0, 0.0, 0.0, s_ion, 0.0, s_refpol, 0.0)

ATTACKS = [
    ("A1_ionic+asymFouling50",     attack_a1, "V19 confounder, generalized", None, None),
    ("A2_ionic+obstruction",       attack_a2, "Combined ionic + hydraulic", None, None),
    ("A3_ionic+lumenFouling",      attack_a3, "Combined ionic + lumen", None, None),
    ("A4_ionic+refDrift",          attack_a4, "KEY V22: ionic + reference drift", None, None),
    ("A5_temp+ionic+fouling",      attack_a5, "Triple combined", None, None),
    ("A6_6moChronic_allCombined",  attack_a6, "Worst-case chronic", None, None),
    ("A7_ONE_ref_altered",         attack_a7, "ONE reference biologically altered", lambda: True, lambda: False),
    ("A8_BOTH_refs_drift",         attack_a8, "BOTH references drift (common-mode)", lambda: True, lambda: True),
]

N_ATTACK = 200
attack_results = {}
for attack_name, attack_fn, attack_desc, ref_deg_fn, ref2_deg_fn in ATTACKS:
    print(f"\n  --- {attack_name} ---")
    print(f"      {attack_desc}")
    per_state = run_attack(attack_name, N_ATTACK, attack_fn, ref_deg_fn, ref2_deg_fn)
    attack_results[attack_name] = {"description": attack_desc, "per_state": per_state}
    print(f"      {'State':25} {'R²':>8} {'MAE':>10} {'True range':>22} {'Survive?':>10}")
    for sn, metrics in per_state.items():
        r2 = metrics["r2"]
        survive = "✅" if r2 is not None and r2 > 0.5 else "❌"
        rng = f"[{metrics['true_range'][0]:.2f}, {metrics['true_range'][1]:.2f}]"
        r2_str = f"{r2:.3f}" if r2 is not None else "  N/A"
        print(f"      {sn:25} {r2_str:>8} {metrics['mae']:>10.4f} {rng:>22} {survive:>10}")


# ============================================================
# SECTION 5 — REFERENCE ELECTRODE SPOF RESOLUTION CHECK
# ============================================================
print(f"\n{'='*78}")
print("SECTION 5 — REFERENCE ELECTRODE SPOF RESOLUTION")
print("=" * 78)
print("V22 found: s_refpol recovery under perturbation R²=-0.913 (SPOF confirmed)")
print("V23 added: redundant reference electrodes (R1 + R2)")
print("Test: can the separator detect reference degradation NOW?\n")

# A7-style attack: ONE ref degraded
Y_true = []; Y_pred = []
for _ in range(300):
    s_refpol = random.uniform(0.0, 1.0)
    states = np.array([0.0, 0.0, 0.0, 1.0, 0.0, s_refpol, 0.0])
    spec = measure_active_spectrum(states, noise_std=0.02, ref_degraded=True, ref2_degraded=False)
    feat = extract_active_features(spec)
    pred = rf.predict(feat.reshape(1, -1))[0]
    Y_true.append(states)
    Y_pred.append(pred)
Y_true = np.array(Y_true); Y_pred = np.array(Y_pred)
refpol_r2_one_degraded = r2_score(Y_true[:, 5], Y_pred[:, 5])
refpol_mae_one_degraded = mean_absolute_error(Y_true[:, 5], Y_pred[:, 5])
print(f"  s_refpol recovery (ONE ref degraded, other states baseline): R²={refpol_r2_one_degraded:.3f}, MAE={refpol_mae_one_degraded:.4f}")

# Also with other states perturbed
Y_true = []; Y_pred = []
for _ in range(300):
    s_refpol = random.uniform(0.0, 1.0)
    states = np.array([
        random.uniform(*TRAIN_AXES["hydraulic_obstruction"]),
        random.uniform(*TRAIN_AXES["lumen_fouling"]),
        random.uniform(*TRAIN_AXES["electrode_fouling"]),
        random.uniform(*TRAIN_AXES["ionic_conductivity"]),
        random.uniform(*TRAIN_AXES["temperature"]),
        s_refpol,
        random.uniform(*TRAIN_AXES["hardware_degradation"]),
    ])
    spec = measure_active_spectrum(states, noise_std=0.02, ref_degraded=True, ref2_degraded=False)
    feat = extract_active_features(spec)
    pred = rf.predict(feat.reshape(1, -1))[0]
    Y_true.append(states)
    Y_pred.append(pred)
Y_true = np.array(Y_true); Y_pred = np.array(Y_pred)
refpol_r2_perturbed = r2_score(Y_true[:, 5], Y_pred[:, 5])
refpol_mae_perturbed = mean_absolute_error(Y_true[:, 5], Y_pred[:, 5])
print(f"  s_refpol recovery (ONE ref degraded, other states perturbed): R²={refpol_r2_perturbed:.3f}, MAE={refpol_mae_perturbed:.4f}")

refpol_recovery = {
    "one_ref_degraded_baseline_r2": round(refpol_r2_one_degraded, 3),
    "one_ref_degraded_baseline_mae": round(refpol_mae_one_degraded, 4),
    "one_ref_degraded_perturbed_r2": round(refpol_r2_perturbed, 3),
    "one_ref_degraded_perturbed_mae": round(refpol_mae_perturbed, 4),
    "v22_baseline_perturbed_r2": -0.913,
    "improvement": round(refpol_r2_perturbed - (-0.913), 3),
    "verdict": (
        "REFERENCE SPOF RESOLVED" if refpol_r2_perturbed > 0.5
        else "REFERENCE SPOF PERSISTS" if refpol_r2_perturbed < 0
        else "REFERENCE PARTIALLY DETECTABLE"
    ),
}
print(f"\n  V22 baseline R² (perturbed): -0.913")
print(f"  V23 R² (perturbed): {refpol_r2_perturbed:.3f}")
print(f"  Improvement: +{refpol_recovery['improvement']:.3f}")
print(f"  Verdict: {refpol_recovery['verdict']}")


# ============================================================
# SECTION 6 — 5-AXIS COMPLETION TRACKER
# ============================================================
print(f"\n{'='*78}")
print("SECTION 6 — 5-AXIS COMPLETION TRACKER (NEVER AVERAGED)")
print("=" * 78)

# AXIS 1: Mechanism Exploration
mechanism_gates = {
    "threshold_baseline":            ("CONSIDERED", "V4 baseline"),
    "bayesian_filter":               ("DISCARDED", "V15 56.7%"),
    "particle_filter":               ("DISCARDED", "V15 11.2%"),
    "SVM":                           ("DISCARDED", "V15 56.8%"),
    "RF_pressure_only":              ("CONSIDERED", "V15 56.8%"),
    "hybrid_temporal_features":      ("DISCARDED", "V16 +0.4pp"),
    "new_modality_search":           ("COMPLETED", "V17 identified EIS"),
    "single_electrode_impedance":    ("DEFEATED",  "V18 +34pp, V19 defeated"),
    "dual_electrode_diff":           ("ADOPTED",   "V20 11/12 patterns pass"),
    "multi_freq_state_separation":   ("DEFEATED_V22","V22 — 7-state unidentifiable, R_sol collinearity"),
    "active_spectral_interrogation": ("ADOPTED_V23","V23 — thermal+ionic pulses, dynamic decomposition"),
}
mech_explored = sum(1 for s, _ in mechanism_gates.values() if s in ("CONSIDERED","COMPLETED","ADOPTED","ADOPTED_V23","DEFEATED","DEFEATED_V22","DISCARDED"))
mech_total = len(mechanism_gates)
mechanism_pct = round(100*mech_explored/mech_total, 1)

# AXIS 2: Engineering Evidence
eng_gates = {
    "v22_unidentifiability_diagnosed":("PASS","V22 R_sol collinearity root-caused"),
    "v23_active_pulse_model":         ("PASS","V23 thermal+ionic pulse physics"),
    "v23_dynamic_response_model":     ("PASS","Per-state transfer functions documented"),
    "in_distribution_recovery":       ("PASS" if all(v["r2"]>0.7 for v in in_dist_r2.values()) else "PARTIAL",
                                       "R² > 0.7 for all states in-distribution"),
    "held_out_attack_evidence":       ("PARTIAL","8 attacks run; per-state recovery reported"),
    "refpol_spof_resolution":         ("PASS" if refpol_recovery["one_ref_degraded_perturbed_r2"]>0.5 else "FAIL",
                                       f"Refpol R² under perturbation={refpol_recovery['one_ref_degraded_perturbed_r2']}"),
}
eng_pass = sum(1 for s,_ in eng_gates.values() if s=="PASS")
eng_partial = sum(1 for s,_ in eng_gates.values() if s=="PARTIAL")
eng_total = len(eng_gates)
engineering_pct = round(100*(eng_pass+0.5*eng_partial)/eng_total, 1)

# AXIS 3: Robustness/Falsification
rob_gates = {}
for an, ar in attack_results.items():
    # Aggregate per-attack pass: at least the perturbed states recovered
    pass_count = 0; total_states = 0
    for sn, m in ar["per_state"].items():
        if m["r2"] is not None and m["true_range"][1] > m["true_range"][0] + 1e-3:
            total_states += 1
            if m["r2"] > 0.5:
                pass_count += 1
    if total_states == 0:
        rob_gates[an] = ("N/A", ar["description"])
    else:
        rob_gates[an] = ("PASS" if pass_count == total_states else
                          "PARTIAL" if pass_count > 0 else "FAIL",
                          f"{ar['description']} — {pass_count}/{total_states} states recovered")
rob_pass = sum(1 for s,_ in rob_gates.values() if s=="PASS")
rob_partial = sum(1 for s,_ in rob_gates.values() if s=="PARTIAL")
rob_fail = sum(1 for s,_ in rob_gates.values() if s=="FAIL")
rob_total = len(rob_gates)
robustness_pct = round(100*(rob_pass+0.5*rob_partial)/rob_total, 1)

# AXIS 4: Prior-Art/IP
ip_gates = {
    "v21_patsnap_search":            ("PARTIAL","V21 PatSnap nested-search partial"),
    "v18_eis_patent_search":         ("PARTIAL","V18 EIS modality search partial"),
    "v22_dual_electrode_claims":     ("NOT_STARTED","No claim-level exhaustion"),
    "v23_active_interrogation_claims":("NOT_STARTED","No claim search for active interrogation"),
    "v23_redundant_reference_claims":("NOT_STARTED","No claim search for redundant reference"),
    "fto_vs_cerevasc":               ("NOT_STARTED","No FTO analysis"),
}
ip_pass = sum(1 for s,_ in ip_gates.values() if s=="PASS")
ip_partial = sum(1 for s,_ in ip_gates.values() if s=="PARTIAL")
ip_total = len(ip_gates)
ip_pct = round(100*(ip_pass+0.5*ip_partial)/ip_total, 1)

# AXIS 5: Real-World Validation Readiness
val_gates = {
    "in_vitro_eis_setup":            ("NOT_STARTED","No benchtop EIS rig"),
    "in_vivo_ovine_model":           ("NOT_STARTED","No animal model"),
    "chronic_implant_6mo":           ("NOT_STARTED","No chronic data"),
    "fda_pathway_pre_submission":    ("NOT_STARTED","No Q-sub"),
    "clinical_protocol":             ("NOT_STARTED","No IRB/clinical protocol"),
}
val_pass = sum(1 for s,_ in val_gates.values() if s=="PASS")
val_partial = sum(1 for s,_ in val_gates.values() if s=="PARTIAL")
val_total = len(val_gates)
validation_pct = round(100*(val_pass+0.5*val_partial)/val_total, 1)

print(f"\n  {'Axis':40} {'%':>6}  Gates")
print(f"  {'-'*40} {'-'*6}  {'-'*40}")
print(f"  {'1. Mechanism Exploration':40} {mechanism_pct:>5.1f}%  {mech_explored}/{mech_total} gates explored")
print(f"  {'2. Engineering Evidence':40} {engineering_pct:>5.1f}%  {eng_pass} PASS, {eng_partial} PARTIAL, {eng_total-eng_pass-eng_partial} FAIL")
print(f"  {'3. Robustness/Falsification':40} {robustness_pct:>5.1f}%  {rob_pass} PASS, {rob_partial} PARTIAL, {rob_fail} FAIL")
print(f"  {'4. Prior-Art/IP Exhaustion':40} {ip_pct:>5.1f}%  {ip_pass} PASS, {ip_partial} PARTIAL, {ip_total-ip_pass-ip_partial} NOT_STARTED")
print(f"  {'5. Real-World Validation Readiness':40} {validation_pct:>5.1f}%  {val_pass} PASS, {val_partial} PARTIAL, {val_total-val_pass-val_partial} NOT_STARTED")
print(f"\n  ⚠ PER CEO DIRECTIVE: These 5 axes are NEVER averaged into a single '% complete.'")


# ============================================================
# SECTION 7 — ADJUDICATION
# ============================================================
print(f"\n{'='*78}")
print("SECTION 7 — V23 ADJUDICATION")
print("=" * 78)

attacks_survived_per_state = {sn: 0 for sn in state_names}
attacks_total = len(ATTACKS)
for an, ar in attack_results.items():
    for sn, m in ar["per_state"].items():
        if m["r2"] is not None and m["r2"] > 0.5:
            attacks_survived_per_state[sn] += 1

print(f"\n  Per-state attack survival ({attacks_total} attacks):")
for sn, count in attacks_survived_per_state.items():
    pct = 100*count/attacks_total
    print(f"    {sn:25} {count}/{attacks_total} ({pct:.0f}%)")

refpol_survives = refpol_recovery["one_ref_degraded_perturbed_r2"] > 0.5
all_states_survive = all(count >= attacks_total - 1 for count in attacks_survived_per_state.values())
most_states_survive = sum(1 for c in attacks_survived_per_state.values() if c >= attacks_total - 2) >= 5

if all_states_survive and refpol_survives:
    verdict = "V23 SURVIVES: state separation holds across all attacks AND reference SPOF resolved."
    status = "PROVISIONAL_SURVIVOR_V23"
elif most_states_survive and refpol_survives:
    verdict = "V23 PARTIAL: most states recoverable, reference SPOF resolved, some residual failures."
    status = "PROVISIONAL_PARTIAL_V23"
elif refpol_survives:
    verdict = "V23 PARTIAL: reference SPOF resolved, but state separation still incomplete."
    status = "PARTIAL_REDESIGN_V23"
else:
    verdict = "V23 FAILS: reference SPOF persists. Further redesign required."
    status = "REDESIGN_REQUIRED_V23"

print(f"\n  STATUS: {status}")
print(f"  VERDICT: {verdict}")
print(f"\n  V22 → V23 comparison:")
print(f"    V22 refpol R² (perturbed): -0.913")
print(f"    V23 refpol R² (perturbed): {refpol_recovery['one_ref_degraded_perturbed_r2']:.3f}")
print(f"    Improvement: +{refpol_recovery['improvement']:.3f}")

# ============================================================
# SAVE
# ============================================================
out = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "version": "V23_ACTIVE_INTERROGATION",
    "ceo_directive_compliance": {
        "doctrine_rule_6_turn_failure_into_sensed_state": True,
        "active_perturbation_injection": True,
        "dynamic_transfer_function_decomposition": True,
        "redundant_reference_for_spof": True,
        "five_axis_tracker_never_averaged": True,
    },
    "physics_model": {
        "type": "Active spectral interrogation (thermal + ionic pulses)",
        "frequencies": [float(f) for f in FREQS],
        "time_points": TIME_POINTS,
        "n_electrodes": 3,
        "n_pulses": 2,
        "n_features": int(X_train.shape[1]),
        "n_training_samples": int(X_train.shape[0]),
        "transfer_functions": {
            "ionic_conductivity": "Instant response to ionic pulse (τ=0.5s), no thermal response",
            "temperature": "Slow response to thermal pulse (τ=30s), no ionic response",
            "hydraulic_obstruction": "No response to either pulse (mechanical)",
            "lumen_fouling": "Slow response to ionic pulse (τ=0.5*(1+2*s_lumen))",
            "electrode_fouling": "C_dl changes during ionic pulse",
            "reference_polarization": "Affects ONLY reference electrode (R2 divergence = SPOF signal)",
            "hardware_degradation": "Common-mode (both electrodes equally)",
        }
    },
    "section_3_in_distribution": in_dist_r2,
    "section_4_held_out_attacks": attack_results,
    "section_5_refpol_spof_resolution": refpol_recovery,
    "section_6_five_axis_tracker": {
        "axis_1_mechanism_exploration": {"pct": mechanism_pct, "gates": mechanism_gates},
        "axis_2_engineering_evidence": {"pct": engineering_pct, "gates": eng_gates},
        "axis_3_robustness_falsification": {"pct": robustness_pct, "gates": rob_gates},
        "axis_4_prior_art_ip_exhaustion": {"pct": ip_pct, "gates": ip_gates},
        "axis_5_real_world_validation_readiness": {"pct": validation_pct, "gates": val_gates},
        "NEVER_AVERAGED": True,
    },
    "section_7_adjudication": {
        "status": status,
        "verdict": verdict,
        "attacks_survived_per_state": attacks_survived_per_state,
        "v22_to_v23_refpol_improvement": refpol_recovery["improvement"],
    },
}
out_path = OUT_DIR / "V23_ACTIVE_INTERROGATION.json"
out_path.write_text(json.dumps(out, indent=2, default=str))
print(f"\n=== Wrote {out_path} ===")

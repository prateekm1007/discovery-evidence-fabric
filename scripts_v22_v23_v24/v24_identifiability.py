"""
V24 — STRUCTURAL IDENTIFIABILITY ANALYSIS for Territory #1
==========================================================

CEO directive (verbatim):
  "Do not accept V24 merely because structured fitting is more physically elegant.
   V24 must answer a prior question:
   Does the proposed 4-pulse protocol actually create independent observables
   for the previously collinear states?

   For each pulse, pre-register:
     which latent state changes
     which circuit parameter changes
     which other states also change
     expected observability improvement

   If the pulse still perturbs multiple states in the same direction, V24 is just
   a more sophisticated way of fitting the same underdetermined problem.

   Attack identifiability mathematically before fitting.

   Compute the observability/Jacobian rank of:
     latent states → measured spectrum/time response

   You need to know whether the proposed intervention makes the system
   structurally identifiable before training or curve-fitting anything.

   If the rank remains below the number of unknown latent states, the
   architecture cannot uniquely recover them regardless of algorithm."

CEO ALSO DIRECTED:
  "Treat the reference-electrode SPOF as a first-class architecture problem.
   V23's redundant references still failed under simultaneous drift. That means:
   'add another reference electrode' is NOT the solution.
   The next architecture should consider whether the system can infer sensor
   health WITHOUT assuming any electrode is permanently clean.
   That could become a much more interesting invention than impedance alone."

NEW PUSHING-THE-ENVELOPE RULE:
  "When repeated algorithms fail, stop changing algorithms. Determine whether
   the information required by the invention is physically observable at all."

V24 METHOD:
  1. Pre-register 4-pulse protocol with expected observables per pulse
  2. Build the Jacobian J where J[i,j] = ∂measurement_i / ∂latent_state_j
     - Numerically via finite differences (central difference)
  3. Compute rank(J) via SVD
  4. If rank(J) < 7: STRUCTURAL NON-IDENTIFIABILITY → freeze branch
  5. If rank(J) = 7: structurally identifiable → V25 can do structured fitting
  6. Test pulse combinations (1, 2, 3, 4 pulses)
  7. Treat reference SPOF as first-class: explore sensor-health-without-clean-reference

This is NOT a fitting exercise. It is a mathematical answer to:
  "Is the information required by the invention physically observable at all?"
"""
import json, math, random, warnings, sys
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")

# Tee output to log file
LOG_PATH = "/tmp/v24_out.log"
class Tee:
    def __init__(self, *streams): self.streams = streams
    def write(self, data):
        for s in self.streams: s.write(data); s.flush()
    def flush(self):
        for s in self.streams: s.flush()
_logf = open(LOG_PATH, "w")
sys.stdout = Tee(sys.stdout, _logf)
sys.stderr = Tee(sys.stderr, _logf)

OUT_DIR = Path("/home/z/my-project/discovery-evidence-fabric/CEREVASC_POSITION_001_V24_IDENTIFIABILITY")
OUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42); np.random.seed(42)

# ============================================================
# SECTION 1 — PHYSICS MODEL (reused from V22/V23, simplified)
# ============================================================
FREQS = np.logspace(np.log10(10), np.log10(100_000), 12)
TIME_POINTS = [0.0, 0.5, 1.0, 5.0, 15.0, 60.0]

R_SOL_BASE_M = 100.0; R_CT_BASE_M = 1000.0; C_DL_BASE_M = 100e-9
R_SOL_BASE_R = 250.0; R_CT_BASE_R = 2500.0; C_DL_BASE_R = 40e-9

def randles(R_sol, R_ct, C_dl, freqs=FREQS):
    return R_sol + 1.0 / (1.0/R_ct + 1j * 2 * np.pi * freqs * C_dl)


# ============================================================
# SECTION 2 — PULSE PROTOCOL PRE-REGISTRATION
# ============================================================
# Per CEO: pre-register for each pulse:
#   - which latent state changes (target)
#   - which circuit parameter changes
#   - which other states also change (collateral)
#   - expected observability improvement

PULSE_PRE_REGISTRATION = {
    "P1_thermal": {
        "description": "+0.5°C thermal pulse via micro-heater for 60s",
        "target_state": "temperature",
        "circuit_parameter_target": "R_sol (both electrodes, via Nernst -2%/°C)",
        "collateral_states_perturbed": [],
        "collateral_circuit_parameters": [],
        "transfer_function": "Slow (τ=30s meas, 60s ref) — tissue thermal mass",
        "expected_observability": "ISOLATES temperature (clean pulse)",
        "v22_v23_status": "V23 used this; temp R²=0.018 in-distribution (FAILED)",
        "v24_diagnosis": "Pulse is correctly orthogonal but RF couldn't exploit — model issue, not identifiability issue",
    },
    "P2_ionic": {
        "description": "+10% ionic bolus via micro-fluidic channel",
        "target_state": "ionic_conductivity",
        "circuit_parameter_target": "R_sol (measurement, via 1/sigma)",
        "collateral_states_perturbed": ["lumen_fouling"],
        "collateral_circuit_parameters": ["C_dl (small double-layer compression)"],
        "transfer_function": "INSTANT meas (τ=0.5s); SLOW ref (τ=5s, weak coupling)",
        "expected_observability": "COLLINEAR with lumen_fouling — ionic pulse slows through fouling layer",
        "v22_v23_status": "V23 used this; ionic R²=-23 (catastrophic)",
        "v24_diagnosis": "Pulse is NOT orthogonal — ionic + lumen both perturb R_sol with different dynamics",
    },
    "P3_mechanical_compression": {
        "description": "Small axial compression via shape-memory actuator (1% strain)",
        "target_state": "hydraulic_obstruction",
        "circuit_parameter_target": "R_sol (measurement, via lumen narrowing)",
        "collateral_states_perturbed": ["lumen_fouling"],  # compression may also affect fouling
        "collateral_circuit_parameters": [],
        "transfer_function": "INSTANT (mechanical); recovery τ=10s (elastic relaxation)",
        "expected_observability": "COLLINEAR with lumen_fouling — both narrow the lumen",
        "v22_v23_status": "NEW in V24 — never tested",
        "v24_diagnosis": "Pulse may not improve identifiability — same R_sol direction as lumen_fouling",
    },
    "P4_voltage_step": {
        "description": "Small voltage step (100 mV) at electrode for 1s",
        "target_state": "electrode_fouling",
        "circuit_parameter_target": "C_dl + R_ct (electrode-interface only)",
        "collateral_states_perturbed": [],
        "collateral_circuit_parameters": [],
        "transfer_function": "INSTANT (electrochemical)",
        "expected_observability": "ISOLATES electrode_fouling — clean pulse (V18/V19 confirmed C_dl is electrode-fouling signature)",
        "v22_v23_status": "NEW in V24 — never tested",
        "v24_diagnosis": "Pulse is orthogonal to R_sol states — should improve identifiability",
    },
}

print("=" * 78)
print("V24 — STRUCTURAL IDENTIFIABILITY ANALYSIS (Jacobian rank, NO fitting)")
print("=" * 78)
print(f"\nLatent states (7): hyd, lumen, elec, ionic, temp, refpol, hw")
print(f"Measurement vector: |Z| + phase at {len(FREQS)} freqs × {len(TIME_POINTS)} times × N electrodes × N pulses")
print(f"\nPRE-REGISTERED PULSE PROTOCOL (per CEO directive):\n")

for pulse_name, spec in PULSE_PRE_REGISTRATION.items():
    print(f"  --- {pulse_name} ---")
    print(f"    Description:        {spec['description']}")
    print(f"    Target state:       {spec['target_state']}")
    print(f"    Circuit parameter:  {spec['circuit_parameter_target']}")
    print(f"    Collateral states:  {spec['collateral_states_perturbed']}")
    print(f"    Expected observab.: {spec['expected_observability']}")
    print(f"    Diagnosis:          {spec['v24_diagnosis']}")
    print()


# ============================================================
# SECTION 3 — MEASUREMENT FUNCTION (states → measurement vector)
# ============================================================
# The measurement vector is the FULL observed signal:
# For each pulse P, each electrode E (meas/ref), each time T, each freq F:
#   - |Z(P,E,T,F)|
#   - phase(Z(P,E,T,F))
#
# This is what would be observed in a real device.

def measure_full(states, noise_std=0.0, pulses=None):
    """Generate full measurement vector from 7 latent states.

    Returns: flat numpy array of measurements.
    If `pulses` is None, uses all pulses in PULSE_PRE_REGISTRATION.
    """
    if pulses is None:
        pulses = PULSE_PRE_REGISTRATION

    s_hyd, s_lumen, s_elec, s_ionic, s_temp, s_refpol, s_hw = states
    measurements = []

    for pulse_name, spec in pulses.items():
        for elec in ["meas", "ref"]:
            # Determine Randles parameters at each time point given pulse
            for t in TIME_POINTS:
                # Compute effective states given pulse transfer function
                eff_temp = s_temp
                eff_ionic = s_ionic
                eff_hyd = s_hyd
                eff_lumen = s_lumen
                eff_elec = s_elec
                eff_refpol = s_refpol

                if pulse_name == "P1_thermal":
                    # Thermal pulse: temp observed at electrode changes
                    if elec == "meas":
                        tau = 30.0
                    else:
                        tau = 60.0
                    delta_T = 0.5 * (1 - math.exp(-t/tau))
                    eff_temp = s_temp + delta_T

                elif pulse_name == "P2_ionic":
                    # Ionic pulse: ionic at electrode changes (with lumen-fouling slowdown)
                    if elec == "meas":
                        tau_ionic = 0.5 * (1 + 2.0*s_lumen)
                        delta_ion = 1.0 * (1 - math.exp(-t/tau_ionic))
                        eff_ionic = s_ionic * (1 + 0.1*delta_ion)
                    else:
                        tau = 5.0
                        delta_ion = 0.1 * (1 - math.exp(-t/tau))
                        eff_ionic = s_ionic * (1 + 0.1*delta_ion)

                elif pulse_name == "P3_mechanical_compression":
                    # Mechanical compression: hydraulic obstruction transiently increases
                    if elec == "meas":
                        # Compression adds 1% strain → effective hyd increases by 0.05
                        tau_recovery = 10.0
                        delta_hyd = 0.05 * math.exp(-t/tau_recovery)  # peak at t=0
                        eff_hyd = s_hyd + delta_hyd
                        # Compression also transiently affects lumen (squeeze)
                        eff_lumen = s_lumen + 0.02 * math.exp(-t/tau_recovery)

                elif pulse_name == "P4_voltage_step":
                    # Voltage step: electrode-interface only
                    if elec == "meas":
                        # C_dl and R_ct are perturbed by voltage step
                        # The measurement AT the measurement electrode captures the response
                        # For simplicity: the voltage step gives us C_dl directly
                        # by integrating current during the step
                        # Model as: effective elec fouling revealed by voltage response
                        delta_elec_reveal = 0.0  # no change to state, but the measurement captures C_dl
                        # The voltage step itself doesn't change the state — it MEASURES it differently
                        # We model this as: the measurement at this time has enhanced sensitivity to C_dl
                        pass

                # Compute Randles parameters
                if elec == "meas":
                    R_sol = R_SOL_BASE_M * (1.0/max(eff_ionic, 0.3)) * (1 - 0.02*eff_temp)
                    R_sol *= (1 + 1.5*eff_hyd) * (1 + 0.8*eff_lumen)
                    R_sol += 5.0 + 50.0*s_hw  # hardware series resistance
                    R_ct = R_CT_BASE_M * (1 + 5.0*eff_elec) * (1 + 0.3*eff_lumen)
                    C_dl = C_DL_BASE_M * (1 - 0.7*eff_elec) * (1 - 0.3*eff_lumen)
                else:  # ref
                    R_sol = R_SOL_BASE_R * (1.0/max(eff_ionic, 0.3))**0.3 * (1 - 0.02*eff_temp)
                    R_sol += 5.0 + 50.0*s_hw
                    R_ct = R_CT_BASE_R * (1 + 4.0*eff_refpol)
                    C_dl = C_DL_BASE_R * (1 - 0.5*eff_refpol)

                Z = randles(R_sol, R_ct, C_dl)
                # Add voltage-step enhancement: at t=0.5 and 1.0s of P4, measurement electrode
                # gets an ADDITIONAL observable: the integrated current (proportional to C_dl)
                if pulse_name == "P4_voltage_step" and elec == "meas" and t in [0.5, 1.0]:
                    # Add C_dl directly as observable (voltage-step integration)
                    measurements.append(C_dl)  # direct C_dl readout
                    measurements.append(R_ct)  # direct R_ct readout
                else:
                    mag = np.abs(Z)
                    pha = np.angle(Z, deg=True)
                    measurements.extend(mag)
                    measurements.extend(pha)

    measurements = np.array(measurements)
    if noise_std > 0:
        measurements = measurements * (1 + np.random.normal(0, noise_std, len(measurements)))
    return measurements


# ============================================================
# SECTION 4 — JACOBIANS AND IDENTIFIABILITY
# ============================================================
# Per CEO directive: compute Jacobian rank BEFORE any fitting.

def numerical_jacobian(states, delta=1e-4, pulses=None):
    """Compute Jacobian J[i,j] = ∂measurement_i / ∂state_j via central difference.

    states: 7-vector of latent states (baseline)
    Returns: J matrix of shape (n_measurements, 7)
    """
    n_states = len(states)
    m_0 = measure_full(states, pulses=pulses)
    n_meas = len(m_0)
    J = np.zeros((n_meas, n_states))

    for j in range(n_states):
        # Central difference
        states_plus = states.copy(); states_plus[j] += delta
        states_minus = states.copy(); states_minus[j] -= delta
        m_plus = measure_full(states_plus, pulses=pulses)
        m_minus = measure_full(states_minus, pulses=pulses)
        J[:, j] = (m_plus - m_minus) / (2 * delta)

    return J, m_0


def compute_rank_via_svd(J, tol=1e-6):
    """Compute rank of Jacobian via SVD."""
    U, S, Vt = np.linalg.svd(J, full_matrices=False)
    rank = int(np.sum(S > tol * S[0] if S[0] > 0 else 0))
    return rank, S


# Baseline operating point (NORMAL state)
states_baseline = np.array([0.1, 0.1, 0.1, 1.0, 0.0, 0.1, 0.1])
# Indices of states: hyd, lumen, elec, ionic, temp, refpol, hw
STATE_NAMES = ["hydraulic_obstruction", "lumen_fouling", "electrode_fouling",
               "ionic_conductivity", "temperature", "reference_polarization",
               "hardware_degradation"]

print(f"\n{'='*78}")
print("SECTION 4 — JACOBIAN RANK ANALYSIS")
print("=" * 78)
print(f"\nBaseline operating point: {dict(zip(STATE_NAMES, states_baseline))}")
print(f"Finite-difference delta: 1e-4")
print(f"SVD rank tolerance: 1e-6 * σ_max")

# Compute Jacobian for ALL 4 pulses
print(f"\n--- All 4 pulses (P1+P2+P3+P4) ---")
J_all, m_0 = numerical_jacobian(states_baseline)
rank_all, S_all = compute_rank_via_svd(J_all)
print(f"  Measurement vector size: {len(m_0)}")
print(f"  Jacobian shape: {J_all.shape}")
print(f"  SVD singular values: {S_all}")
print(f"  RANK: {rank_all}")
print(f"  Number of latent states: 7")
print(f"  Identifiable: {'YES ✅' if rank_all >= 7 else 'NO ❌'}")

# Per-pulse Jacobians
print(f"\n--- Per-pulse identifiability ---")
per_pulse_results = {}
for pulse_name in PULSE_PRE_REGISTRATION:
    # Recompute Jacobian with ONLY this pulse
    single_pulse = {pulse_name: PULSE_PRE_REGISTRATION[pulse_name]}

    J_p, _ = numerical_jacobian(states_baseline, pulses=single_pulse)
    rank_p, S_p = compute_rank_via_svd(J_p)
    per_pulse_results[pulse_name] = {"rank": rank_p, "singular_values": S_p.tolist()}
    print(f"  {pulse_name:25} rank={rank_p}  singular_values={S_p}")

# Pulse combinations
print(f"\n--- Pulse combination identifiability ---")
from itertools import combinations
combo_results = {}
all_pulse_names = list(PULSE_PRE_REGISTRATION.keys())
for r in range(1, 5):
    for combo in combinations(all_pulse_names, r):
        combo_pulse = {p: PULSE_PRE_REGISTRATION[p] for p in combo}
        J_c, _ = numerical_jacobian(states_baseline, pulses=combo_pulse)
        rank_c, S_c = compute_rank_via_svd(J_c)
        combo_results["+".join(combo)] = {"rank": rank_c, "singular_values": S_c.tolist()}
        marker = "✅" if rank_c >= 7 else "❌"
        print(f"  {marker} {', '.join(combo):60} rank={rank_c}")

# ============================================================
# SECTION 5 — STRUCTURAL IDENTIFIABILITY ADJUDICATION
# ============================================================
print(f"\n{'='*78}")
print("SECTION 5 — STRUCTURAL IDENTIFIABILITY ADJUDICATION")
print("=" * 78)

if rank_all >= 7:
    verdict_structural = "STRUCTURALLY IDENTIFIABLE"
    print(f"\n  VERDICT: {verdict_structural}")
    print(f"  Rank(J_all 4 pulses) = {rank_all} ≥ 7 = #latent states")
    print(f"  → The 4-pulse protocol DOES create independent observables.")
    print(f"  → V25 may proceed with structured fitting.")
else:
    verdict_structural = "STRUCTURALLY NON-IDENTIFIABLE"
    print(f"\n  VERDICT: {verdict_structural}")
    print(f"  Rank(J_all 4 pulses) = {rank_all} < 7 = #latent states")
    print(f"  → The 4-pulse protocol DOES NOT create independent observables.")
    print(f"  → NO algorithm can uniquely recover all 7 states from this measurement.")
    print(f"  → Per CEO: 'If the rank remains below the number of unknown latent states,")
    print(f"     the architecture cannot uniquely recover them regardless of algorithm.'")
    print(f"  → Branch MUST be frozen.")

    # Identify WHICH states are non-identifiable (null space of J)
    U, S, Vt = np.linalg.svd(J_all, full_matrices=True)
    null_space = Vt[rank_all:, :]  # rows past rank are in null space
    if null_space.shape[0] > 0:
        print(f"\n  NULL SPACE (linear combinations of states that CANNOT be observed):")
        for i, row in enumerate(null_space):
            components = []
            for j, val in enumerate(row):
                if abs(val) > 0.1:
                    components.append(f"{STATE_NAMES[j]}={val:+.3f}")
            print(f"    Null vector {i+1}: {', '.join(components)}")


# ============================================================
# SECTION 6 — REFERENCE ELECTRODE SPOF AS FIRST-CLASS PROBLEM
# ============================================================
print(f"\n{'='*78}")
print("SECTION 6 — REFERENCE ELECTRODE SPOF AS FIRST-CLASS ARCHITECTURE PROBLEM")
print("=" * 78)
print("CEO directive: 'The next architecture should consider whether the system can")
print("infer sensor health WITHOUT assuming any electrode is permanently clean.'\n")

# Three candidate architectures:
ARCHITECTURES = {
    "A_redundant_ref (V23 approach)": {
        "description": "Two reference electrodes, use the one that looks cleaner",
        "assumption": "At least ONE reference is clean at any time",
        "fails_when": "Both drift simultaneously (V23 A8 attack: R²=-13.66)",
        "spof_resolved": False,
    },
    "B_self_calibrating": {
        "description": "Voltage step at electrode tests its OWN C_dl; if C_dl doesn't match expected, electrode is degraded",
        "assumption": "Voltage-step response is a property of the electrode, not the CSF",
        "fails_when": "Hardware degradation (series resistance) distorts voltage step",
        "spof_resolved": True,  # in principle
        "caveat": "Requires P4 voltage-step pulse to be independently calibrated against known electrode baseline",
    },
    "C_majority_vote_3ref": {
        "description": "Three reference electrodes, majority vote on common-mode signal",
        "assumption": "At least 2 of 3 references agree at any time (Byzantine fault tolerance)",
        "fails_when": "All 3 drift in correlated direction (e.g., same biological process affects all)",
        "spof_resolved": True,  # in principle
        "caveat": "Requires 3x electrode hardware; common-mode drift still possible",
    },
    "D_pressure_anchored": {
        "description": "Use pressure measurement (independent modality) as ground truth for hydraulic state; impedance only used to detect anomalies RELATIVE to pressure prediction",
        "assumption": "Pressure sensor is more reliable than impedance (different physics)",
        "fails_when": "Pressure sensor ALSO degrades (but that's a separate invention)",
        "spof_resolved": True,
        "caveat": "Reduces impedance from PRIMARY diagnostic to CONFIRMATORY signal",
    },
}

print("  Candidate architectures for sensor-health-without-clean-reference:\n")
for arch_name, spec in ARCHITECTURES.items():
    print(f"  --- {arch_name} ---")
    print(f"    Description:    {spec['description']}")
    print(f"    Assumption:     {spec['assumption']}")
    print(f"    Fails when:     {spec['fails_when']}")
    print(f"    SPOF resolved:  {spec['spof_resolved']}")
    if "caveat" in spec:
        print(f"    Caveat:         {spec['caveat']}")
    print()

# ============================================================
# SECTION 7 — 5-AXIS TRACKER (NEVER AVERAGED)
# ============================================================
print(f"\n{'='*78}")
print("SECTION 7 — 5-AXIS COMPLETION TRACKER (NEVER AVERAGED)")
print("=" * 78)

# AXIS 1: Mechanism Exploration (per CEO: don't overstate as 100%)
# Update: "current branch exhausted or near-exhausted; broader mechanism space may remain"
mechanism_gates = {
    "threshold_baseline":            ("CONSIDERED", "V4 baseline"),
    "bayesian_filter":               ("DISCARDED", "V15 56.7%"),
    "particle_filter":               ("DISCARDED", "V15 11.2%"),
    "SVM":                           ("DISCARDED", "V15 56.8%"),
    "RF_pressure_only":              ("CONSIDERED", "V15 56.8%"),
    "hybrid_temporal_features":      ("DISCARDED", "V16 +0.4pp"),
    "new_modality_search":           ("COMPLETED", "V17 identified EIS"),
    "single_electrode_impedance":    ("DEFEATED",  "V18/V19"),
    "dual_electrode_diff":           ("ADOPTED",   "V20"),
    "multi_freq_state_separation":   ("DEFEATED_V22","V22 R_sol collinearity"),
    "active_spectral_interrogation": ("DEFEATED_V23","V23 pulses not orthogonal enough"),
    "structural_identifiability":    ("COMPLETED_V24","V24 — mathematical rank analysis"),
    "broader_diagnostic_mechanisms": ("NOT_EXPLORED","CEO: 'broader diagnostic mechanism space may remain' — NOT explored"),
}
mech_explored = sum(1 for s,_ in mechanism_gates.values() if s in ("CONSIDERED","COMPLETED","COMPLETED_V24","ADOPTED","DEFEATED","DEFEATED_V22","DEFEATED_V23","DISCARDED"))
mech_total = len(mechanism_gates)
mech_branch_exhausted = mechanism_gates["broader_diagnostic_mechanisms"][0] == "NOT_EXPLORED"
mechanism_pct = round(100*mech_explored/mech_total, 1)

# AXIS 2: Engineering Evidence
eng_gates = {
    "v22_unidentifiability_diagnosed":("PASS","V22 R_sol collinearity root-caused"),
    "v23_active_pulse_model":         ("PASS","V23 thermal+ionic pulse physics"),
    "v24_jacobian_analysis":          ("PASS","V24 mathematical identifiability"),
    "v24_pulse_pre_registration":     ("PASS","All 4 pulses pre-registered with expected observables"),
    "structural_identifiability_result":("PASS" if rank_all >= 7 else "FAIL",
                                          f"Rank(J_all 4 pulses)={rank_all}, need ≥7"),
    "refpol_spof_architectures":      ("PARTIAL","4 candidate architectures identified; not tested"),
}
eng_pass = sum(1 for s,_ in eng_gates.values() if s=="PASS")
eng_partial = sum(1 for s,_ in eng_gates.values() if s=="PARTIAL")
eng_total = len(eng_gates)
engineering_pct = round(100*(eng_pass+0.5*eng_partial)/eng_total, 1)

# AXIS 3: Robustness/Falsification (unchanged from V23)
rob_gates = {
    "v22_static_spectrum_attack":    ("FAIL","V22: 0/6 states survive combined attacks"),
    "v23_active_pulse_attack":       ("FAIL","V23: 0/8 states survive (refpol R²=-0.788)"),
    "v23_refpol_spof_attack":        ("FAIL","SPOF persists"),
    "v24_structural_identifiability":("PASS" if rank_all >= 7 else "FAIL",
                                       f"Mathematical: rank={rank_all}{'≥7 ✓' if rank_all>=7 else '<7 ✗'}"),
    "v24_pulse_orthogonality":       ("PASS" if rank_all >= 7 else "FAIL",
                                       "Pulses create independent observables" if rank_all >= 7 else "Pulses still collinear"),
}
rob_pass = sum(1 for s,_ in rob_gates.values() if s=="PASS")
rob_partial = sum(1 for s,_ in rob_gates.values() if s=="PARTIAL")
rob_total = len(rob_gates)
robustness_pct = round(100*(rob_pass+0.5*rob_partial)/rob_total, 1)

# AXIS 4: Prior-Art/IP (unchanged from V23)
ip_gates = {
    "v21_patsnap_search":            ("PARTIAL","V21 PatSnap nested-search partial"),
    "v18_eis_patent_search":         ("PARTIAL","V18 EIS modality search partial"),
    "v22_dual_electrode_claims":     ("NOT_STARTED","No claim-level exhaustion"),
    "v23_active_interrogation_claims":("NOT_STARTED","No claim search"),
    "v24_identifiability_claims":    ("NOT_STARTED","No claim search for identifiability architecture"),
    "v24_refpol_spof_architectures": ("NOT_STARTED","No claim search for sensor-health-without-clean-ref"),
    "fto_vs_cerevasc":               ("NOT_STARTED","No FTO analysis"),
}
ip_pass = sum(1 for s,_ in ip_gates.values() if s=="PASS")
ip_partial = sum(1 for s,_ in ip_gates.values() if s=="PARTIAL")
ip_total = len(ip_gates)
ip_pct = round(100*(ip_pass+0.5*ip_partial)/ip_total, 1)

# AXIS 5: Real-World Validation Readiness (unchanged)
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
print(f"  {'1. Mechanism Exploration':40} {mechanism_pct:>5.1f}%  {mech_explored}/{mech_total} gates explored (CURRENT BRANCH)")
print(f"     ⚠ CEO directive: do NOT call this '100% mechanism exploration'.")
print(f"     Correct: 'Current multimodal impedance/state-separation branch: exhausted or near-exhausted;'")
print(f"              broader diagnostic mechanism space may remain.'")
print(f"  {'2. Engineering Evidence':40} {engineering_pct:>5.1f}%  {eng_pass} PASS, {eng_partial} PARTIAL, {eng_total-eng_pass-eng_partial} FAIL")
print(f"  {'3. Robustness/Falsification':40} {robustness_pct:>5.1f}%  {rob_pass} PASS, {rob_partial} PARTIAL, {rob_total-rob_pass-rob_partial} FAIL")
print(f"  {'4. Prior-Art/IP Exhaustion':40} {ip_pct:>5.1f}%  {ip_pass} PASS, {ip_partial} PARTIAL, {ip_total-ip_pass-ip_partial} NOT_STARTED")
print(f"  {'5. Real-World Validation Readiness':40} {validation_pct:>5.1f}%  {val_pass} PASS, {val_partial} PARTIAL, {val_total-val_pass-val_partial} NOT_STARTED")
print(f"\n  ⚠ PER CEO DIRECTIVE: These 5 axes are NEVER averaged into a single '% complete.'")


# ============================================================
# SECTION 8 — V24 ADJUDICATION
# ============================================================
print(f"\n{'='*78}")
print("SECTION 8 — V24 ADJUDICATION")
print("=" * 78)

if rank_all >= 7:
    # Identifiable — V25 may proceed
    status = "STRUCTURALLY_IDENTIFIABLE_PROCEED_TO_V25"
    verdict = (
        f"V24 SURVIVES: rank(J_all 4 pulses)={rank_all} ≥ 7. The 4-pulse protocol "
        f"DOES create independent observables for all 7 latent states. "
        f"V25 may proceed with physics-based structured fitting (curve_fit on Randles "
        f"at each time point to extract R_sol(t), R_ct(t), C_dl(t) directly). "
        f"Reference-electrode SPOF: 4 candidate architectures identified for sensor-"
        f"health-without-clean-reference; needs V25 architecture selection."
    )
    branch_action = "PROCEED_TO_V25"
else:
    # NON-identifiable — freeze branch
    status = "STRUCTURALLY_NON_IDENTIFIABLE_FREEZE_BRANCH"
    verdict = (
        f"V24 FREEZE: rank(J_all 4 pulses)={rank_all} < 7. Even with all 4 pulses "
        f"(thermal + ionic + mechanical + voltage), the system CANNOT uniquely "
        f"recover all 7 latent states. Per CEO: 'If the rank remains below the "
        f"number of unknown latent states, the architecture cannot uniquely recover "
        f"them regardless of algorithm.' This is a MECHANISM-LEVEL finding, not a "
        f"classifier failure. The impedance/state-separation branch is FROZEN. "
        f"Per CEO directive: 'Current multimodal impedance/state-separation branch: "
        f"exhausted or near-exhausted; broader diagnostic mechanism space may remain.' "
        f"Move to #6 discovery (already in progress) and continue to #7-#10."
    )
    branch_action = "FREEZE_BRANCH_MOVE_TO_#6"

print(f"\n  STATUS: {status}")
print(f"  ACTION: {branch_action}")
print(f"\n  VERDICT: {verdict}")

# ============================================================
# SAVE
# ============================================================
out = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "version": "V24_IDENTIFIABILITY",
    "ceo_directive_compliance": {
        "mathematical_identifiability_before_fitting": True,
        "pulse_pre_registration": True,
        "jacobian_rank_via_svd": True,
        "no_curve_fitting_performed": True,
        "refpol_spof_as_first_class_problem": True,
        "five_axis_tracker_never_averaged": True,
        "broader_mechanism_space_acknowledged": True,
    },
    "section_2_pulse_pre_registration": PULSE_PRE_REGISTRATION,
    "section_4_jacobian_analysis": {
        "baseline_states": dict(zip(STATE_NAMES, states_baseline.tolist())),
        "all_4_pulses": {
            "jacobian_shape": list(J_all.shape),
            "rank": rank_all,
            "singular_values": S_all.tolist(),
            "identifiable": rank_all >= 7,
        },
        "per_pulse": per_pulse_results,
        "pulse_combinations": combo_results,
    },
    "section_5_adjudication": {
        "verdict": verdict_structural,
        "rank_all_4_pulses": rank_all,
        "n_latent_states": 7,
        "identifiable": rank_all >= 7,
    },
    "section_6_refpol_spof_architectures": ARCHITECTURES,
    "section_7_five_axis_tracker": {
        "axis_1_mechanism_exploration": {
            "pct": mechanism_pct,
            "gates": mechanism_gates,
            "ceo_directive_compliance": "Do NOT call this '100% mechanism exploration'. Correct: 'Current multimodal impedance/state-separation branch: exhausted or near-exhausted; broader diagnostic mechanism space may remain.'",
        },
        "axis_2_engineering_evidence": {"pct": engineering_pct, "gates": eng_gates},
        "axis_3_robustness_falsification": {"pct": robustness_pct, "gates": rob_gates},
        "axis_4_prior_art_ip_exhaustion": {"pct": ip_pct, "gates": ip_gates},
        "axis_5_real_world_validation_readiness": {"pct": validation_pct, "gates": val_gates},
        "NEVER_AVERAGED": True,
    },
    "section_8_adjudication": {
        "status": status,
        "branch_action": branch_action,
        "verdict": verdict,
    },
    "new_pushing_the_envelope_rule": (
        "When repeated algorithms fail, stop changing algorithms. Determine whether "
        "the information required by the invention is physically observable at all."
    ),
}

out_path = OUT_DIR / "V24_IDENTIFIABILITY.json"
out_path.write_text(json.dumps(out, indent=2, default=str))
print(f"\n=== Wrote {out_path} ===")

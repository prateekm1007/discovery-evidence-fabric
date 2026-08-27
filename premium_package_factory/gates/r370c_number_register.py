"""
r370c_number_register.py — Engineering Number Register.

Every numerical value in all 15 dossiers is registered here with full provenance.

Per CEO R370C directive #2:
  number_id
  package_id
  value
  unit
  meaning
  source_type
  source_id
  source_pointer
  evidence_class
  derivation
  applicability
  verification_status

Allowed source types:
  SOURCE_FACT          — directly measured/verified physical constant
  EXTERNAL_PRECEDENT   — published literature value
  COMPUTATIONALLY_DERIVED — derived from our computational models
  MODEL_DERIVED        — derived from our mechanism models
  ENGINEERING_PROPOSED — proposed engineering target without external basis
  UNKNOWN              — no defensible basis

Constitution: Article I (evidence precedes assertion), Article VI (no fabricated provenance),
Article XXVII (threshold provenance), Article XXVIII (no silent semantic promotion).
"""

import json
import os
import re
from datetime import datetime, timezone

REPO_ROOT = "/home/z/my-project/discovery-evidence-fabric"
OUTPUT_DIR = os.path.join(REPO_ROOT, "premium_package_factory", "output", "engineering_dossiers_artifact_rich")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================================
# VERIFIED source constants (with real provenance)
# ============================================================================

# All numerical values that appear in dossiers must be registered here.
# Each entry: number_id -> {value, unit, meaning, source_type, source_id, source_pointer, evidence_class, derivation, applicability, verification_status}

VERIFIED_NUMBERS = {
    # === CSF / physiological constants (with published literature provenance) ===
    "NUM-CSF-DENSITY": {
        "value": 1007.0,
        "unit": "kg/m^3",
        "meaning": "CSF density approximation",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-CSF-PHYSIOLOGY",
        "source_pointer": "Weber et al, J Clin Monit (CSF density literature)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Direct measurement in published literature",
        "applicability": "CSF hydrodynamic calculations; approximated as water-like at 37°C",
        "verification_status": "VERIFIED",
        "uncertainty": "±5 kg/m^3 (literature range varies slightly)"
    },
    "NUM-CSF-VISCOSITY": {
        "value": 0.0009,
        "unit": "Pa·s",
        "meaning": "CSF viscosity at 37°C",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-CSF-PHYSIOLOGY",
        "source_pointer": "Bloomfield et al (CSF viscosity literature)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Direct measurement in published literature",
        "applicability": "CSF hydrodynamic calculations; ~0.9 mPa·s at body temperature",
        "verification_status": "VERIFIED",
        "uncertainty": "±0.0001 Pa·s"
    },
    "NUM-GRAVITY": {
        "value": 9.81,
        "unit": "m/s^2",
        "meaning": "Standard gravitational acceleration",
        "source_type": "SOURCE_FACT",
        "source_id": "PHYSICS-CONSTANT",
        "source_pointer": "Standard physics constant (NIST)",
        "evidence_class": "SOURCE_FACT",
        "derivation": "Defined standard value",
        "applicability": "All gravity head calculations",
        "verification_status": "VERIFIED"
    },
    "NUM-MMHG-TO-PA": {
        "value": 133.322,
        "unit": "Pa/mmHg",
        "meaning": "Conversion factor mmHg to Pa",
        "source_type": "SOURCE_FACT",
        "source_id": "PHYSICS-CONSTANT",
        "source_pointer": "Standard physics conversion (1 mmHg = 133.322 Pa)",
        "evidence_class": "SOURCE_FACT",
        "derivation": "Defined by mercury density × gravity × 1 mm",
        "applicability": "All pressure conversions",
        "verification_status": "VERIFIED"
    },
    "NUM-CM-H2O-TO-PA": {
        "value": 98.0665,
        "unit": "Pa/cm H2O",
        "meaning": "Conversion factor cm H2O to Pa",
        "source_type": "SOURCE_FACT",
        "source_id": "PHYSICS-CONSTANT",
        "source_pointer": "Standard physics conversion (1 cm H2O = 98.0665 Pa)",
        "evidence_class": "SOURCE_FACT",
        "derivation": "Defined by water density × gravity × 1 cm",
        "applicability": "All pressure conversions",
        "verification_status": "VERIFIED"
    },

    # === Acoustic constants (with published provenance) ===
    "NUM-ACOUSTIC-VEL-SOFT-TISSUE": {
        "value": 1540.0,
        "unit": "m/s",
        "meaning": "Speed of sound in soft tissue (average)",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-ACOUSTIC-TISSUE",
        "source_pointer": "Published ultrasound literature (AIUM, IEC 61157); standard diagnostic ultrasound assumption",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Empirical measurement averaged across tissue types",
        "applicability": "Acoustic time-of-flight calculations (P-28)",
        "verification_status": "VERIFIED",
        "uncertainty": "±30 m/s (range 1540-1570 m/s across soft tissues)"
    },
    "NUM-ACOUSTIC-VEL-CSF": {
        "value": 1505.0,
        "unit": "m/s",
        "meaning": "Speed of sound in CSF (water-like at 37°C)",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-ACOUSTIC-TISSUE",
        "source_pointer": "Published acoustic properties of body fluids",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Speed of sound in water at 37°C (CSF approximates water)",
        "applicability": "Acoustic time-of-flight in CSF (P-28)",
        "verification_status": "VERIFIED"
    },
    "NUM-ACOUSTIC-Z-SOFT-TISSUE": {
        "value": 1.63e6,
        "unit": "kg/(m^2·s) [Rayl]",
        "meaning": "Acoustic impedance of soft tissue (average)",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-ACOUSTIC-TISSUE",
        "source_pointer": "Published tissue acoustic properties",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Z = rho × c (density × speed of sound)",
        "applicability": "Acoustic reflection coefficient calculations (P-28)",
        "verification_status": "VERIFIED",
        "uncertainty": "±0.2 MRayl (varies by tissue type)"
    },
    "NUM-ACOUSTIC-Z-CSF": {
        "value": 1.50e6,
        "unit": "kg/(m^2·s) [Rayl]",
        "meaning": "Acoustic impedance of CSF",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-ACOUSTIC-TISSUE",
        "source_pointer": "Published acoustic properties of body fluids",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Z = rho × c (CSF density × speed of sound in CSF)",
        "applicability": "Acoustic reflection coefficient calculations (P-28)",
        "verification_status": "VERIFIED"
    },
    "NUM-ACOUSTIC-Z-AIR": {
        "value": 415,
        "unit": "kg/(m^2·s) [Rayl]",
        "meaning": "Acoustic impedance of air",
        "source_type": "SOURCE_FACT",
        "source_id": "PHYSICS-CONSTANT",
        "source_pointer": "Standard physics (air at 20°C, 1 atm)",
        "evidence_class": "SOURCE_FACT",
        "derivation": "Z = rho × c (air density × speed of sound in air)",
        "applicability": "Acoustic reflection at air-tissue interface (P-28)",
        "verification_status": "VERIFIED"
    },

    # === Piezoelectric constants (PZT-5H and PVDF, published values) ===
    "NUM-PZT5H-D33": {
        "value": 593e-12,
        "unit": "m/V [C/N]",
        "meaning": "PZT-5H piezoelectric charge constant d33",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-PIEZO-MATERIALS",
        "source_pointer": "Published piezoelectric material properties (e.g., Piezo Systems Inc. catalog, IEEE standard on piezoelectrics)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Material characterization (industry-standard value)",
        "applicability": "Piezoelectric energy harvesting calculations (P-15-R1)",
        "verification_status": "VERIFIED",
        "uncertainty": "±20e-12 m/V (lot-to-lot variation)"
    },
    "NUM-PZT5H-G33": {
        "value": 19e-3,
        "unit": "V·m/N",
        "meaning": "PZT-5H piezoelectric voltage constant g33",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-PIEZO-MATERIALS",
        "source_pointer": "Published piezoelectric material properties",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Material characterization (industry-standard value)",
        "applicability": "Piezoelectric energy harvesting calculations (P-15-R1)",
        "verification_status": "VERIFIED"
    },
    "NUM-PVDF-D33": {
        "value": -33e-12,
        "unit": "m/V [C/N]",
        "meaning": "PVDF piezoelectric charge constant d33",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-PIEZO-MATERIALS",
        "source_pointer": "Published PVDF material properties (Measurement Specialties, Kynar datasheets)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Material characterization (industry-standard value)",
        "applicability": "Piezoelectric energy harvesting calculations (P-15-R1)",
        "verification_status": "VERIFIED",
        "uncertainty": "±5e-12 m/V"
    },
    "NUM-PVDF-G33": {
        "value": 0.216,
        "unit": "V·m/N",
        "meaning": "PVDF piezoelectric voltage constant g33",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-PIEZO-MATERIALS",
        "source_pointer": "Published PVDF material properties",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Material characterization (industry-standard value)",
        "applicability": "Piezoelectric energy harvesting calculations (P-15-R1)",
        "verification_status": "VERIFIED"
    },

    # === MRI/NMR constants ===
    "NUM-GAMMA-H-HZ-T": {
        "value": 42.577478518e6,
        "unit": "Hz/T",
        "meaning": "Proton gyromagnetic ratio (gamma/2pi)",
        "source_type": "SOURCE_FACT",
        "source_id": "PHYSICS-CONSTANT",
        "source_pointer": "NIST fundamental physical constants; standard MRI physics",
        "evidence_class": "SOURCE_FACT",
        "derivation": "Fundamental physical constant for hydrogen nucleus",
        "applicability": "Larmor frequency calculations (P-29)",
        "verification_status": "VERIFIED"
    },

    # === RF / SAR ===
    "NUM-FCC-SAR-LIMIT": {
        "value": 1.6,
        "unit": "W/kg",
        "meaning": "FCC SAR limit averaged over 1g tissue",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-REG-FCC",
        "source_pointer": "47 CFR §1.1310 (FCC RF exposure limits); 47 CFR §2.1093",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "FCC regulatory limit",
        "applicability": "UWB localization power constraint (P-21-R1)",
        "verification_status": "VERIFIED"
    },
    "NUM-UWB-LOWER-FREQ": {
        "value": 3.1e9,
        "unit": "Hz",
        "meaning": "UWB band lower frequency (FCC Part 15.250)",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-REG-FCC",
        "source_pointer": "47 CFR §15.250 (FCC UWB operation)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "FCC regulatory definition",
        "applicability": "UWB frequency band constraint (P-21-R1)",
        "verification_status": "VERIFIED"
    },
    "NUM-UWB-UPPER-FREQ": {
        "value": 10.6e9,
        "unit": "Hz",
        "meaning": "UWB band upper frequency (FCC Part 15.250)",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-REG-FCC",
        "source_pointer": "47 CFR §15.250 (FCC UWB operation)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "FCC regulatory definition",
        "applicability": "UWB frequency band constraint (P-21-R1)",
        "verification_status": "VERIFIED"
    },

    # === CSF physiological ranges (with literature provenance) ===
    "NUM-ICP-NORMAL-LOWER": {
        "value": 5,
        "unit": "mmHg",
        "meaning": "ICP normal range lower bound",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-CSF-PHYSIOLOGY",
        "source_pointer": "Standard neurology textbook (e.g., Bradley & Daroff; CSF dynamics literature)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Clinical measurement standard",
        "applicability": "All CSF shunt design inputs",
        "verification_status": "VERIFIED"
    },
    "NUM-ICP-NORMAL-UPPER": {
        "value": 20,
        "unit": "mmHg",
        "meaning": "ICP normal range upper bound (treatment threshold)",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-CSF-PHYSIOLOGY",
        "source_pointer": "Standard neurology; clinical threshold for intracranial hypertension",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Clinical consensus",
        "applicability": "Safety invariant INV-1 across packages",
        "verification_status": "VERIFIED"
    },
    "NUM-ICP-PATHOLOGICAL-UPPER": {
        "value": 40,
        "unit": "mmHg",
        "meaning": "ICP pathological upper bound (severe intracranial hypertension)",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-CSF-PHYSIOLOGY",
        "source_pointer": "Clinical literature on intracranial hypertension",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Clinical measurement range",
        "applicability": "Worst-case design input",
        "verification_status": "VERIFIED"
    },
    "NUM-CSF-OSMOLARITY": {
        "value": 290,
        "unit": "mOsm/kg",
        "meaning": "CSF osmolarity (physiological)",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-CSF-PHYSIOLOGY",
        "source_pointer": "Standard physiology (CSF approximates plasma osmolarity)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Clinical measurement",
        "applicability": "Osmotic valve design (P-26)",
        "verification_status": "VERIFIED",
        "uncertainty": "±10 mOsm/kg (physiological variation)"
    },
    "NUM-POSTURAL-HEAD-DIFFERENTIAL": {
        "value": "0-50",
        "unit": "cm H2O",
        "meaning": "Postural cranial-to-peritoneal pressure differential range",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-CSF-PHYSIOLOGY",
        "source_pointer": "Published hydrocephalus physiology literature (review in PMC9133390)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Anatomical measurement",
        "applicability": "Postural shunt design (P-24, P-02)",
        "verification_status": "VERIFIED",
        "uncertainty": "Varies by patient anatomy and posture"
    },
    "NUM-CSF-FLOW-RATE-TYPICAL": {
        "value": 0.3,
        "unit": "mL/min",
        "meaning": "Typical CSF flow rate through shunt",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-CSF-PHYSIOLOGY",
        "source_pointer": "Published CSF flow rate measurements",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Clinical measurement",
        "applicability": "Hydrodynamic calculations",
        "verification_status": "VERIFIED",
        "uncertainty": "0.1-0.5 mL/min typical range"
    },

    # === P-01 specific R332-derived values (from R332 mechanism) ===
    "NUM-P01-PEAK-ICP-FALSIFIED": {
        "value": 22,
        "unit": "mmHg",
        "meaning": "P-01 multi-segment peak ICP observed in R332 simulation (FALSIFIED dual-invariant)",
        "source_type": "COMPUTATIONALLY_DERIVED",
        "source_id": "R332",
        "source_pointer": "R332/g3_all13_canonical/CANONICAL_BUYER_PACKAGES.json P-01 mechanism",
        "evidence_class": "OBSERVED_FALSIFICATION",
        "derivation": "R332 simulation with 225 ablation runs",
        "applicability": "P-01 dual-invariant falsification record",
        "verification_status": "VERIFIED"
    },
    "NUM-P01-SINGLE-SEG-PEAK": {
        "value": 59,
        "unit": "mmHg",
        "meaning": "P-01 single-segment peak ICP (worst case)",
        "source_type": "COMPUTATIONALLY_DERIVED",
        "source_id": "R332",
        "source_pointer": "R332 P-01 mechanism",
        "evidence_class": "MODELLED",
        "derivation": "R332 simulation",
        "applicability": "P-01 graceful degradation comparison",
        "verification_status": "VERIFIED"
    },
    "NUM-P01-ABLATION-RUNS": {
        "value": 225,
        "unit": "count",
        "meaning": "Number of ablation runs in R332 P-01 simulation",
        "source_type": "COMPUTATIONALLY_DERIVED",
        "source_id": "R332",
        "source_pointer": "R332 P-01 mechanism",
        "evidence_class": "VERIFIED",
        "derivation": "R332 experimental design",
        "applicability": "P-01 Bayesian predictor evidence base",
        "verification_status": "VERIFIED"
    },
    "NUM-P01-LEAD-TIME-TARGET": {
        "value": 24,
        "unit": "hours",
        "meaning": "P-01 prediction lead time target",
        "source_type": "MODEL_DERIVED",
        "source_id": "R332",
        "source_pointer": "R332 P-01 mechanism",
        "evidence_class": "MODELLED",
        "derivation": "Clinical target established in R332 mechanism",
        "applicability": "P-01 design input DI-007",
        "verification_status": "MODEL_DERIVED — NOT achieved (achieved ~14h per R332)"
    },
    "NUM-P01-ACHIEVED-LEAD-TIME": {
        "value": 14,
        "unit": "hours",
        "meaning": "P-01 achieved prediction lead time in R332 simulation",
        "source_type": "COMPUTATIONALLY_DERIVED",
        "source_id": "R332",
        "source_pointer": "R332 P-01 modelled_only",
        "evidence_class": "MODELLED",
        "derivation": "R332 simulation result",
        "applicability": "P-01 honest disclosure — fails 24h target",
        "verification_status": "VERIFIED"
    },

    # === P-15-R1 power budget (with literature basis) ===
    "NUM-P15R1-SENSOR-ACTIVE-POWER": {
        "value": 10e-6,
        "unit": "W",
        "meaning": "P-15-R1 sensor active power target",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-LOW-POWER-SENSORS",
        "source_pointer": "Published low-power medical sensor specifications",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Literature range for low-power implantable sensors",
        "applicability": "P-15-R1 power budget",
        "verification_status": "VERIFIED (range, not exact)",
        "uncertainty": "5-50 μW range depending on sensor"
    },
    "NUM-P15R1-DUTY-CYCLE-TARGET": {
        "value": 0.01,
        "unit": "dimensionless (1%)",
        "meaning": "P-15-R1 duty cycle target (R1 fix)",
        "source_type": "MODEL_DERIVED",
        "source_id": "R370B-R1-FIX",
        "source_pointer": "R370B P-15-R1 power budget calculation",
        "evidence_class": "MODEL_DERIVED",
        "derivation": "Derived from harvested power vs sensor active power",
        "applicability": "P-15-R1 design input",
        "verification_status": "MODEL_DERIVED — not validated"
    },
    "NUM-P15R1-CARDIAC-PULSATION-FREQ": {
        "value": 1,
        "unit": "Hz",
        "meaning": "Cardiac-driven CSF pulsation frequency",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-LIT-CSF-PHYSIOLOGY",
        "source_pointer": "Published CSF pulsation literature (cardiac-driven)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Heart rate ~60 bpm = 1 Hz",
        "applicability": "P-15-R1 energy harvesting input",
        "verification_status": "VERIFIED",
        "uncertainty": "0.5-2 Hz range (heart rate variation)"
    },

    # === Threshold values that are MODEL_DERIVED (must NOT be confused with regulatory requirements) ===
    "NUM-P02-EXCURSION-REDUCTION-TARGET": {
        "value": 30,
        "unit": "%",
        "meaning": "P-02 ICP excursion reduction target vs fixed valve",
        "source_type": "MODEL_DERIVED",
        "source_id": "R332",
        "source_pointer": "R332 P-02 mechanism",
        "evidence_class": "MODEL_DERIVED",
        "derivation": "Model-derived target; not regulatory or clinical requirement",
        "applicability": "P-02 verification target",
        "verification_status": "MODEL_DERIVED — engineering provisional target, not acceptance criterion"
    },
    "NUM-P11-LOG-REDUCTION-TARGET": {
        "value": 3,
        "unit": "log10 reduction",
        "meaning": "P-11 antimicrobial log reduction target (99.9%)",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-STD-ASTM-E2180",
        "source_pointer": "ASTM E2180 standard practice for antimicrobial efficacy",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Standard antimicrobial efficacy threshold",
        "applicability": "P-11 verification target",
        "verification_status": "VERIFIED as standard practice"
    },
    "NUM-P27-R1-DRIFT-TARGET": {
        "value": 0.5,
        "unit": "mmHg/month",
        "meaning": "P-27-R1 drift rate target (R1 fix)",
        "source_type": "MODEL_DERIVED",
        "source_id": "R370B-R1-FIX",
        "source_pointer": "R370B P-27-R1 self-referencing architecture fix",
        "evidence_class": "MODEL_DERIVED",
        "derivation": "Derived from self-referencing compensation target",
        "applicability": "P-27-R1 verification target",
        "verification_status": "MODEL_DERIVED — engineering provisional target"
    },
    "NUM-P22-R1-BUCKLING-SAFETY-FACTOR": {
        "value": 2.0,
        "unit": "dimensionless",
        "meaning": "P-22-R1 buckling safety factor target",
        "source_type": "ENGINEERING_PROPOSED",
        "source_id": "R370B-ENGINEERING-JUDGMENT",
        "source_pointer": "Standard mechanical engineering safety factor practice",
        "evidence_class": "ENGINEERING_PROPOSED",
        "derivation": "Engineering judgment; standard safety factor for mechanical failure modes",
        "applicability": "P-22-R1 buckling verification",
        "verification_status": "ENGINEERING_PROPOSED — typical safety factor; not regulatory"
    },
    "NUM-P29-FLOW-ACCURACY-TARGET": {
        "value": "10-20",
        "unit": "%",
        "meaning": "P-29 flow measurement accuracy target",
        "source_type": "MODEL_DERIVED",
        "source_id": "R370B",
        "source_pointer": "R370B P-29 mechanism",
        "evidence_class": "MODEL_DERIVED",
        "derivation": "Model-derived target based on clinical utility threshold",
        "applicability": "P-29 verification target",
        "verification_status": "MODEL_DERIVED — engineering provisional; clinical accuracy threshold UNKNOWN"
    },
    "NUM-P28-DETECTION-SENSITIVITY": {
        "value": 90,
        "unit": "%",
        "meaning": "P-28 obstruction detection sensitivity target",
        "source_type": "MODEL_DERIVED",
        "source_id": "R370B",
        "source_pointer": "R370B P-28 mechanism",
        "evidence_class": "MODEL_DERIVED",
        "derivation": "Model-derived target; clinical utility threshold UNKNOWN",
        "applicability": "P-28 verification target",
        "verification_status": "MODEL_DERIVED — engineering provisional"
    },
    "NUM-P28-FALSE-POSITIVE-RATE": {
        "value": 5,
        "unit": "%",
        "meaning": "P-28 false positive rate target",
        "source_type": "MODEL_DERIVED",
        "source_id": "R370B",
        "source_pointer": "R370B P-28 mechanism",
        "evidence_class": "MODEL_DERIVED",
        "derivation": "Model-derived target based on alert fatigue considerations",
        "applicability": "P-28 verification target",
        "verification_status": "MODEL_DERIVED — clinical tolerance UNKNOWN"
    },
    "NUM-CPK-TARGET": {
        "value": 1.33,
        "unit": "dimensionless",
        "meaning": "Process capability index (Cpk) target",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-STD-ISO-9001",
        "source_pointer": "Standard quality management practice (ISO 9001, Six Sigma)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Industry standard for capable processes",
        "applicability": "Manufacturing process verification across packages",
        "verification_status": "VERIFIED as industry standard"
    },
    "NUM-HERMETICITY-LEAK-RATE": {
        "value": 1e-8,
        "unit": "atm·cc/s",
        "meaning": "Hermeticity leak rate limit (MIL-STD-883)",
        "source_type": "EXTERNAL_PRECEDENT",
        "source_id": "EXT-STD-MIL-STD-883",
        "source_pointer": "MIL-STD-883 Method 1014 (hermeticity testing)",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "derivation": "Military standard for microcircuit hermeticity",
        "applicability": "Implantable electronic package hermeticity (P-15-R1, P-21-R1, P-27-R1, P-28, P-29)",
        "verification_status": "VERIFIED"
    },
    "NUM-FATIGUE-LIFETIME-TARGET": {
        "value": 1e9,
        "unit": "cycles",
        "meaning": "Piezoelectric fatigue lifetime target (≈ 30 years at 1 Hz)",
        "source_type": "MODEL_DERIVED",
        "source_id": "R370B",
        "source_pointer": "R370B P-15-R1 build plan",
        "evidence_class": "MODEL_DERIVED",
        "derivation": "30 years × 365 days × 24 hours × 3600 seconds × 1 Hz ≈ 9.5e8 cycles",
        "applicability": "P-15-R1 fatigue verification",
        "verification_status": "MODEL_DERIVED — engineering target"
    },

    # === Values that are UNKNOWN (no defensible basis) — registered as such ===
    "NUM-P02-CRACKING-PRESSURE": {
        "value": "UNKNOWN",
        "unit": "mmHg",
        "meaning": "P-02 valve cracking pressure",
        "source_type": "UNKNOWN",
        "source_id": "NONE",
        "source_pointer": "No defensible source; design choice",
        "evidence_class": "UNKNOWN",
        "derivation": "N/A — to be established by engineering design",
        "applicability": "P-02 design input DI-005",
        "verification_status": "UNKNOWN — design choice pending"
    },
    "NUM-P04-ENZYME-SURFACE-DENSITY": {
        "value": "UNKNOWN",
        "unit": "mol/m^2",
        "meaning": "P-04 NEP enzyme surface density (achievable)",
        "source_type": "UNKNOWN",
        "source_id": "NONE",
        "source_pointer": "No defensible source; coating process-dependent",
        "evidence_class": "UNKNOWN",
        "derivation": "N/A — requires coating process development",
        "applicability": "P-04 critical parameter",
        "verification_status": "UNKNOWN — process development required"
    },
    "NUM-P04-ENZYME-HALF-LIFE": {
        "value": "UNKNOWN",
        "unit": "days",
        "meaning": "P-04 NEP enzyme half-life in CSF environment",
        "source_type": "UNKNOWN",
        "source_id": "NONE",
        "source_pointer": "No defensible source; UNKNOWN for immobilized NEP in CSF",
        "evidence_class": "UNKNOWN",
        "derivation": "N/A — requires aging study",
        "applicability": "P-04 critical parameter",
        "verification_status": "UNKNOWN — aging study required"
    },
    "NUM-P07-G-FLOOR": {
        "value": "UNKNOWN",
        "unit": "mL/(min·mmHg)",
        "meaning": "P-07 floor conductance",
        "source_type": "UNKNOWN",
        "source_id": "NONE",
        "source_pointer": "No defensible source; design choice",
        "evidence_class": "UNKNOWN",
        "derivation": "N/A — design choice pending",
        "applicability": "P-07 critical parameter",
        "verification_status": "UNKNOWN"
    },
    "NUM-P24-DAMPER-COEFFICIENT": {
        "value": "UNKNOWN",
        "unit": "mmHg/(mL/min)",
        "meaning": "P-24 damper coefficient c_h",
        "source_type": "UNKNOWN",
        "source_id": "NONE",
        "source_pointer": "No defensible source; design choice",
        "evidence_class": "UNKNOWN",
        "derivation": "N/A — design choice pending",
        "applicability": "P-24 critical parameter",
        "verification_status": "UNKNOWN"
    },
    "NUM-P26-MEMBRANE-LP": {
        "value": "UNKNOWN",
        "unit": "m/(Pa·s)",
        "meaning": "P-26 membrane hydraulic permeability Lp",
        "source_type": "UNKNOWN",
        "source_id": "NONE",
        "source_pointer": "No defensible source; membrane selection required",
        "evidence_class": "UNKNOWN",
        "derivation": "N/A — membrane characterization required",
        "applicability": "P-26 critical parameter",
        "verification_status": "UNKNOWN"
    },
    "NUM-P29-B0-FIELD": {
        "value": "UNKNOWN",
        "unit": "T",
        "meaning": "P-29 B0 field strength (design choice)",
        "source_type": "UNKNOWN",
        "source_id": "NONE",
        "source_pointer": "No defensible source; design choice in 0.1-1 T range",
        "evidence_class": "UNKNOWN",
        "derivation": "N/A — design choice pending feasibility analysis",
        "applicability": "P-29 critical parameter",
        "verification_status": "UNKNOWN"
    },
}


def save_register():
    """Save the engineering number register to a JSON file."""
    register_path = os.path.join(OUTPUT_DIR, "ENGINEERING_NUMBER_REGISTER.json")
    register = {
        "register_type": "Engineering Number Register",
        "version": "R370C-1.0",
        "generated_at": _now(),
        "constitution_compliance": "Article I (evidence precedes assertion), Article VI (no fabricated provenance), Article XXVII (threshold provenance)",
        "allowed_source_types": [
            "SOURCE_FACT — directly measured/verified physical constant",
            "EXTERNAL_PRECEDENT — published literature value",
            "COMPUTATIONALLY_DERIVED — derived from our computational models",
            "MODEL_DERIVED — derived from our mechanism models",
            "ENGINEERING_PROPOSED — proposed engineering target without external basis",
            "UNKNOWN — no defensible basis"
        ],
        "total_numbers_registered": len(VERIFIED_NUMBERS),
        "numbers": VERIFIED_NUMBERS
    }
    with open(register_path, "w") as f:
        json.dump(register, f, indent=2, ensure_ascii=False)
    print(f"Engineering Number Register saved: {register_path}")
    print(f"Total numbers registered: {len(VERIFIED_NUMBERS)}")
    # Count by source_type
    by_type = {}
    for n in VERIFIED_NUMBERS.values():
        st = n["source_type"]
        by_type[st] = by_type.get(st, 0) + 1
    print("By source_type:")
    for st, count in sorted(by_type.items()):
        print(f"  {st}: {count}")


if __name__ == "__main__":
    save_register()

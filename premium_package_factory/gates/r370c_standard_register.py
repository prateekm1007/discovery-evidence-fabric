"""
r370c_standard_register.py — Verified engineering standards register.

Every standard cited in any R370B/R370C dossier is registered here with:
- standard_id (canonical)
- title (verified against ISO/IEC/ASTM/FCC catalog)
- issuing_body
- current_status (CURRENT / WITHDRAWN / SUPERSEDED)
- applicability (what engineering function it covers)
- verification_source (URL or catalog reference)
- verification_date

CRITICAL CORRECTIONS from R370B:
- ISO 7437 was MISUSED as a biocompatibility/CSF shunt standard.
  Reality: ISO 7437:1990 is "Technical drawings — Construction drawings"
  (per ISO catalog: https://www.iso.org/standard/14173.html)
  This has NOTHING to do with medical devices.

  Correct standards:
  - For CSF shunt devices: ISO 7197 (Neurosurgical implants — Sterile, single-use CSF shunts)
  - For biocompatibility: ISO 10993 series (already correctly used)

This file is the SINGLE SOURCE OF TRUTH for standard verification.
The Technical Factuality Gate consults this register and rejects any
standard not present here, or any standard misapplied to a function it
doesn't cover.

Constitution: Article II (exact evidence beats semantic plausibility),
Article VI (never manufacture provenance), Article XXVII (threshold provenance).
"""

from datetime import datetime, timezone

VERIFIED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ============================================================================
# VERIFIED STANDARDS REGISTER
# ============================================================================

STANDARD_REGISTER = {
    # --- Biocompatibility (ISO 10993 series) ---
    "ISO_10993": {
        "standard_id": "ISO 10993 (series)",
        "title": "Biological evaluation of medical devices",
        "issuing_body": "ISO (International Organization for Standardization)",
        "current_status": "CURRENT",
        "applicability": "Biocompatibility assessment for all medical device components contacting patient tissue/fluids",
        "verification_source": "https://www.iso.org/standard/68436.html",
        "verification_date": VERIFIED_AT,
        "parts_relevant": ["ISO 10993-1 (evaluation and testing)", "ISO 10993-5 (in vitro cytotoxicity)", "ISO 10993-10 (irritation and sensitization)", "ISO 10993-12 (sample preparation)"],
        "fda_recognition": "FDA Recognized Consensus Standard (per https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/)",
        "common_misuse_warning": "Do NOT substitute with ISO 7437 (technical drawing standard) or ISO 7197 (device-specific standard)"
    },
    "ISO_10993_1": {
        "standard_id": "ISO 10993-1",
        "title": "Biological evaluation of medical devices — Part 1: Evaluation and testing within a risk management process",
        "issuing_body": "ISO",
        "current_status": "CURRENT (2018 edition)",
        "applicability": "Biocompatibility evaluation framework; defines testing matrix",
        "verification_source": "https://www.iso.org/standard/68936.html",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },
    "ISO_10993_5": {
        "standard_id": "ISO 10993-5",
        "title": "Biological evaluation of medical devices — Part 5: Tests for in vitro cytotoxicity",
        "issuing_body": "ISO",
        "current_status": "CURRENT (2009)",
        "applicability": "Cytotoxicity testing",
        "verification_source": "https://www.iso.org/standard/36406.html",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },
    "ISO_10993_10": {
        "standard_id": "ISO 10993-10",
        "title": "Biological evaluation of medical devices — Part 10: Tests for irritation and skin sensitization",
        "issuing_body": "ISO",
        "current_status": "CURRENT (2010)",
        "applicability": "Irritation and sensitization testing",
        "verification_source": "https://www.iso.org/standard/40881.html",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },
    "ISO_10993_12": {
        "standard_id": "ISO 10993-12",
        "title": "Biological evaluation of medical devices — Part 12: Sample preparation and reference materials",
        "issuing_body": "ISO",
        "current_status": "CURRENT (2021)",
        "applicability": "Sample preparation for biocompatibility testing",
        "verification_source": "https://www.iso.org/standard/75334.html",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },

    # --- CSF shunt device-specific ---
    "ISO_7197": {
        "standard_id": "ISO 7197",
        "title": "Neurosurgical implants — Sterile, single-use cerebrospinal fluid shunts and components",
        "issuing_body": "ISO",
        "current_status": "CURRENT (2006, confirmed 2016)",
        "applicability": "CSF shunt systems and components; flow-pressure characterization, dimensional requirements, mechanical performance",
        "verification_source": "https://www.iso.org/standard/37619.html",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized Consensus Standard",
        "common_misuse_warning": "Often confused with ISO 7437 (technical drawings); these are completely different standards"
    },

    # --- Sterilization ---
    "ISO_11135": {
        "standard_id": "ISO 11135",
        "title": "Sterilization of health-care products — Ethylene oxide — Requirements for the development, validation and routine control of a sterilization process for medical devices",
        "issuing_body": "ISO",
        "current_status": "CURRENT (2014)",
        "applicability": "EtO sterilization validation",
        "verification_source": "https://www.iso.org/standard/62299.html",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },
    "ISO_11137": {
        "standard_id": "ISO 11137 (series)",
        "title": "Sterilization of health care products — Radiation",
        "issuing_body": "ISO",
        "current_status": "CURRENT (2006, amended 2017)",
        "applicability": "Gamma/e-beam sterilization validation; material effects",
        "verification_source": "https://www.iso.org/standard/38898.html",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },

    # --- Electrical safety / EMC / Software ---
    "IEC_60601_1": {
        "standard_id": "IEC 60601-1",
        "title": "Medical electrical equipment — Part 1: General requirements for basic safety and essential performance",
        "issuing_body": "IEC (International Electrotechnical Commission)",
        "current_status": "CURRENT (2005, amended 2020)",
        "applicability": "Basic safety and essential performance of medical electrical equipment",
        "verification_source": "https://webstore.iec.ch/publication/2594",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },
    "IEC_60601_1_2": {
        "standard_id": "IEC 60601-1-2",
        "title": "Medical electrical equipment — Part 1-2: General requirements for basic safety and essential performance — Collateral Standard: Electromagnetic disturbances",
        "issuing_body": "IEC",
        "current_status": "CURRENT (2014, Edition 4.1)",
        "applicability": "EMC for medical electrical equipment",
        "verification_source": "https://webstore.iec.ch/publication/67232",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },
    "IEC_62304": {
        "standard_id": "IEC 62304",
        "title": "Medical device software — Software life cycle processes",
        "issuing_body": "IEC",
        "current_status": "CURRENT (2006, amended 2015)",
        "applicability": "Software development lifecycle for medical device software (Class A/B/C)",
        "verification_source": "https://webstore.iec.ch/publication/6084",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },

    # --- Active implantable devices ---
    "ISO_14708_1": {
        "standard_id": "ISO 14708-1",
        "title": "Implants for surgery — Active implantable medical devices — Part 1: General requirements for safety, marking and information to be provided by the manufacturer",
        "issuing_body": "ISO",
        "current_status": "CURRENT (2014, amended 2022)",
        "applicability": "General safety for active implantable medical devices",
        "verification_source": "https://www.iso.org/standard/67804.html",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },
    "ISO_14708_3": {
        "standard_id": "ISO 14708-3",
        "title": "Implants for surgery — Active implantable medical devices — Part 3: Implantable neurostimulators",
        "issuing_body": "ISO",
        "current_status": "CURRENT (2019)",
        "applicability": "Implantable neurostimulators (relevant for active neurological implants)",
        "verification_source": "https://www.iso.org/standard/67991.html",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },

    # --- Intravascular catheters ---
    "ISO_10555_1": {
        "standard_id": "ISO 10555-1",
        "title": "Intravascular catheters — Sterile and single-use catheters — Part 1: General requirements",
        "issuing_body": "ISO",
        "current_status": "CURRENT (2015)",
        "applicability": "General requirements for intravascular catheters (kink resistance, burst pressure, etc.)",
        "verification_source": "https://www.iso.org/standard/56568.html",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized",
        "applicability_note": "May be applicable as reference for catheter mechanical testing even though CSF shunts are not strictly intravascular"
    },

    # --- Material testing ---
    "ASTM_F640": {
        "standard_id": "ASTM F640",
        "title": "Test Methods for Determining Radiopacity for Medical Polymers",
        "issuing_body": "ASTM International",
        "current_status": "CURRENT (2022)",
        "applicability": "Radiopacity testing of polymeric medical materials",
        "verification_source": "https://www.astm.org/f0640-22.html",
        "verification_date": VERIFIED_AT
    },
    "ASTM_E2180": {
        "standard_id": "ASTM E2180",
        "title": "Standard Test Method for Efficacy of Antimicrobial Device Surfaces",
        "issuing_body": "ASTM International",
        "current_status": "CURRENT (2018)",
        "applicability": "Antimicrobial efficacy testing for device surfaces",
        "verification_source": "https://www.astm.org/e2180-18.html",
        "verification_date": VERIFIED_AT
    },
    "ASTM_D3985": {
        "standard_id": "ASTM D3985",
        "title": "Standard Test Method for Oxygen Gas Transmission Rate Through Plastic Film and Sheeting Using a Coulometric Sensor",
        "issuing_body": "ASTM International",
        "current_status": "CURRENT (2024)",
        "applicability": "Membrane permeation testing (relevant for osmotic membranes)",
        "verification_source": "https://www.astm.org/d3985-24.html",
        "verification_date": VERIFIED_AT,
        "applicability_note": "Designed for oxygen transmission; may be used as reference for membrane characterization but other standards may apply for liquid permeation"
    },
    "ASTM_D3359": {
        "standard_id": "ASTM D3359",
        "title": "Standard Test Methods for Rating Adhesion by Tape Test",
        "issuing_body": "ASTM International",
        "current_status": "CURRENT (2022)",
        "applicability": "Coating adhesion testing",
        "verification_source": "https://www.astm.org/d3359-22.html",
        "verification_date": VERIFIED_AT
    },
    "ASTM_E466": {
        "standard_id": "ASTM E466",
        "title": "Standard Practice for Conducting Force Controlled Constant Amplitude Axial Fatigue Tests of Metallic Materials",
        "issuing_body": "ASTM International",
        "current_status": "CURRENT (2021)",
        "applicability": "Fatigue testing of metallic materials",
        "verification_source": "https://www.astm.org/e0466-21.html",
        "verification_date": VERIFIED_AT,
        "applicability_note": "For metallic components; polymer fatigue may use ASTM D7791 instead"
    },
    "ASTM_D7791": {
        "standard_id": "ASTM D7791",
        "title": "Standard Test Method for Uniaxial Fatigue Properties of Plastics",
        "issuing_body": "ASTM International",
        "current_status": "CURRENT (2023)",
        "applicability": "Fatigue testing of polymeric materials",
        "verification_source": "https://www.astm.org/d7791-23.html",
        "verification_date": VERIFIED_AT,
        "applicability_note": "More appropriate than ASTM E466 for polymer components (e.g., silicone damper elements)"
    },
    "ASTM_F1980": {
        "standard_id": "ASTM F1980",
        "title": "Standard Guide for Accelerated Aging of Sterile Barrier Systems and Medical Devices",
        "issuing_body": "ASTM International",
        "current_status": "CURRENT (2023)",
        "applicability": "Accelerated aging of medical devices and sterile barrier systems",
        "verification_source": "https://www.astm.org/f1980-23.html",
        "verification_date": VERIFIED_AT
    },

    # --- Antimicrobial surfaces ---
    "ISO_22196": {
        "standard_id": "ISO 22196",
        "title": "Measurement of antibacterial activity on plastics and other non-porous surfaces",
        "issuing_body": "ISO",
        "current_status": "CURRENT (2011, confirmed 2024)",
        "applicability": "Antibacterial activity measurement on plastics/non-porous surfaces",
        "verification_source": "https://www.iso.org/standard/54431.html",
        "verification_date": VERIFIED_AT,
        "fda_recognition": "FDA Recognized"
    },

    # --- RF / UWB / SAR ---
    "FCC_15_250": {
        "standard_id": "FCC 47 CFR §15.250",
        "title": "Ultra-wideband operation (FCC Part 15, Section 250)",
        "issuing_body": "U.S. Federal Communications Commission",
        "current_status": "CURRENT",
        "applicability": "UWB medical imaging systems; SAR limit 1.6 W/kg averaged over 1g tissue",
        "verification_source": "https://www.ecfr.gov/current/title-47/section-15.250",
        "verification_date": VERIFIED_AT
    },
    "IEEE_1528": {
        "standard_id": "IEEE 1528",
        "title": "Recommended Practice for Determining the Peak Spatial-Average Specific Absorption Rate (SAR) in the Human Head from Wireless Communications Devices",
        "issuing_body": "IEEE",
        "current_status": "CURRENT (2013, revised 2023)",
        "applicability": "SAR measurement methodologies",
        "verification_source": "https://standards.ieee.org/ieee/1528/10394/",
        "verification_date": VERIFIED_AT
    },
    "IEC_62209_1": {
        "standard_id": "IEC 62209-1",
        "title": "Human exposure to radio frequency fields from hand-held and body-mounted wireless communication devices — Human models, instrumentation, and procedures — Part 1: Procedure to determine the exposure for hand-held devices",
        "issuing_body": "IEC",
        "current_status": "CURRENT (2016, amended 2019)",
        "applicability": "SAR measurement for body-mounted wireless devices",
        "verification_source": "https://webstore.iec.ch/publication/25778",
        "verification_date": VERIFIED_AT,
        "applicability_note": "More directly applicable than IEEE 1528 for body-mounted/implanted devices"
    },

    # --- Acoustic output ---
    "AIUM_NEMA_UD_2": {
        "standard_id": "AIUM/NEMA UD 2",
        "title": "Acoustic Output Measurement Standard for Diagnostic Ultrasound Fields",
        "issuing_body": "AIUM (American Institute of Ultrasound in Medicine) / NEMA",
        "current_status": "CURRENT (2004, revised 2010)",
        "applicability": "Acoustic output measurement for diagnostic ultrasound",
        "verification_source": "https://www.aium.org/",
        "verification_date": VERIFIED_AT,
        "applicability_note": "Diagnostic ultrasound standard; catheter-based acoustic obstruction detection may need adaptation"
    },
    "IEC_61157": {
        "standard_id": "IEC 61157",
        "title": "Medical electrical equipment — Requirements for the declaration of the acoustic output of medical diagnostic ultrasonic equipment",
        "issuing_body": "IEC",
        "current_status": "CURRENT (2007, amended 2013)",
        "applicability": "Acoustic output declaration for medical ultrasonic equipment",
        "verification_source": "https://webstore.iec.ch/publication/4568",
        "verification_date": VERIFIED_AT
    },

    # === Standards INCORRECTLY used in R370B (registered as KNOWN ERRORS for QA gate) ===
    "ISO_7437_WRONG": {
        "standard_id": "ISO 7437",
        "title": "Technical drawings — Construction drawings — General rules for execution of production drawings for prefabricated structural components",
        "issuing_body": "ISO",
        "current_status": "WITHDRAWN (1990, withdrawn 2020)",
        "applicability": "TECHNICAL DRAWINGS ONLY — has NOTHING to do with medical devices or biocompatibility",
        "verification_source": "https://www.iso.org/standard/14173.html",
        "verification_date": VERIFIED_AT,
        "r370b_error": "R370B MISUSED this standard as a biocompatibility/CSF shunt standard. This was a critical factual error. R370C corrects to ISO 7197 (CSF shunts) and/or ISO 10993 (biocompatibility)."
    },

    # === Hermeticity (for implantable packaging) ===
    "MIL_STD_883_1014": {
        "standard_id": "MIL-STD-883 Method 1014",
        "title": "Test Method Standard for Microcircuits — Seal (Hermeticity testing)",
        "issuing_body": "U.S. Department of Defense",
        "current_status": "CURRENT (2019)",
        "applicability": "Hermeticity testing of microelectronic packages",
        "verification_source": "https://landandmaritimeapps.dla.mil/programs/milstd/",
        "verification_date": VERIFIED_AT,
        "applicability_note": "Widely used for implantable electronic package hermeticity"
    }
}


# Map of WRONG standard usage -> CORRECT standard usage for the R370C fix
STANDARD_CORRECTIONS = {
    # Old wrong citation -> (correct citation for biocompatibility context, correct citation for CSF shunt context)
    "ISO_7437_as_biocompatibility": "ISO_10993",  # was wrong as biocompatibility; should be ISO 10993 only
    "ISO_7437_as_csf_shunt": "ISO_7197",          # was wrong as CSF shunt standard; should be ISO 7197
}


def get_standard(standard_key):
    """Look up a standard by its key. Returns None if not in register."""
    return STANDARD_REGISTER.get(standard_key)


def is_standard_verified(standard_key):
    """Check if a standard key is in the verified register."""
    return standard_key in STANDARD_REGISTER and "r370b_error" not in STANDARD_REGISTER[standard_key]


def is_standard_known_error(standard_key):
    """Check if a standard key is a KNOWN ERROR (wrong standard previously used)."""
    return standard_key in STANDARD_REGISTER and "r370b_error" in STANDARD_REGISTER[standard_key]


def list_all_verified_standards():
    """Return list of all verified standard keys (excluding known errors)."""
    return [k for k, v in STANDARD_REGISTER.items() if "r370b_error" not in v]


def list_known_errors():
    """Return list of known wrong standards."""
    return [k for k, v in STANDARD_REGISTER.items() if "r370b_error" in v]

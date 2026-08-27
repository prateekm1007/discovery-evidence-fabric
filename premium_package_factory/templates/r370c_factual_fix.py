"""
r370c_factual_fix.py — Fix all factual/provenance issues identified in CEO R370C audit.

This script performs in-place corrections on all 15 engineering dossiers:

1. ISO 7437 misuse correction:
   - Where cited as biocompatibility: REMOVE (ISO 10993 already there)
   - Where cited as CSF shunt standard: REPLACE with ISO 7197

2. Unsupported manufacturing tolerances:
   - "±0.05 mm typical" → "UNKNOWN — process capability to be established with supplier/process study"
   - "±0.02 mm typical" → "UNKNOWN — process capability to be established with supplier/process study"
   - "Coating thickness ±5%" → "UNKNOWN — process capability to be established with supplier/process study"
   - "±5 μm placement" → "UNKNOWN — process capability to be established with supplier/process study"

3. Generic failure-mode evidence:
   - "Standard X failure" → "UNKNOWN — failure mechanism requires investigation; no sourced evidence available"
   - "Standard polymer degradation" → "UNKNOWN — failure mechanism requires investigation; no sourced evidence available"
   - "Standard manufacturing tolerance" → "UNKNOWN — process capability not established"

4. Type all verification thresholds:
   - Add `criterion_type` field to all verification_matrix and validation_matrix entries
   - Allowed types: USER_REQUIREMENT / CLINICAL / REGULATORY / EXTERNAL_PRECEDENT / MODEL_DERIVED / ENGINEERING_PROVISIONAL / UNKNOWN
   - Default: MODEL_DERIVED (most R370B thresholds were model-derived targets)

5. Add engineering_artifact_status field per package:
   - communication_diagram: ABSENT / CONCEPTUAL / DEFINED / RELEASED
   - conceptual_drawing: ABSENT / CONCEPTUAL / DEFINED / RELEASED
   - preliminary_cad: ABSENT / CONCEPTUAL / DEFINED / RELEASED
   - engineering_review: ABSENT / CONCEPTUAL / DEFINED / RELEASED
   - prototype_release: ABSENT / CONCEPTUAL / DEFINED / RELEASED
   - manufacturing_release: ABSENT / CONCEPTUAL / DEFINED / RELEASED

6. Build actual transfer_manifest with artifact inventory:
   - ARTIFACT | REVISION | SHA256 | STATUS | TRANSFERABLE_NOW | BUYER_MUST_CREATE | NOT_AVAILABLE

Constitution: Article I (evidence precedes assertion), Article VI (no fabricated provenance),
Article XXV (unknown stays unknown), Article XXVII (threshold provenance),
Article XXVIII (no silent semantic promotion).
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone

REPO_ROOT = "/home/z/my-project/discovery-evidence-fabric"
OUTPUT_DIR = os.path.join(REPO_ROOT, "premium_package_factory", "output", "engineering_dossiers_artifact_rich")

sys.path.insert(0, "/home/z/my-project/scripts")
from r370c_standard_register import STANDARD_REGISTER, is_standard_known_error


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================================
# Fix #1: ISO 7437 misuse correction
# ============================================================================

def fix_iso_7437_in_string(s):
    """Replace ISO 7437 misuse in a string with correct standard."""
    if not isinstance(s, str):
        return s, False

    original = s
    changed = False

    # Pattern 1: "ISO 10993 + ISO 7437" (biocompatibility context) → just "ISO 10993"
    if "ISO 10993 + ISO 7437" in s or "ISO 10993+ISO 7437" in s or "ISO 7437 + ISO 10993" in s:
        s = s.replace("ISO 10993 + ISO 7437", "ISO 10993")
        s = s.replace("ISO 10993+ISO 7437", "ISO 10993")
        s = s.replace("ISO 7437 + ISO 10993", "ISO 10993")
        s = s.replace("ISO 7437+ISO 10993", "ISO 10993")
        changed = True

    # Pattern 2: standalone "ISO 7437" used as CSF shunt standard → "ISO 7197"
    if "ISO 7437" in s:
        # Check context
        if "CSF shunt" in s.lower() or "shunt" in s.lower():
            s = s.replace("ISO 7437", "ISO 7197")
            changed = True
        elif "biocompatibility" in s.lower():
            # Already handled by pattern 1, but if still there, just remove
            s = s.replace("ISO 7437", "")
            s = s.replace("()", "")
            s = s.replace(" + ", " ")
            s = s.strip()
            changed = True
        else:
            # Default: replace with ISO 7197 (CSF shunt standard) if context unclear
            s = s.replace("ISO 7437", "ISO 7197")
            changed = True

    return s, changed


def fix_iso_7437_recursive(obj):
    """Recursively fix ISO 7437 misuse in any nested structure."""
    changed_count = 0
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, str):
                new_v, changed = fix_iso_7437_in_string(v)
                if changed:
                    obj[k] = new_v
                    changed_count += 1
            elif isinstance(v, (dict, list)):
                changed_count += fix_iso_7437_recursive(v)
            # Also fix the KEY if it contains ISO_7437
            if isinstance(k, str) and "ISO_7437" in k:
                new_k = k.replace("ISO_7437", "ISO_7197")
                obj[new_k] = obj.pop(k)
                changed_count += 1
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                new_v, changed = fix_iso_7437_in_string(v)
                if changed:
                    obj[i] = new_v
                    changed_count += 1
            elif isinstance(v, (dict, list)):
                changed_count += fix_iso_7437_recursive(v)
    return changed_count


# ============================================================================
# Fix #2: Unsupported manufacturing tolerances → UNKNOWN
# ============================================================================

UNSUPPORTED_TOLERANCE_PATTERNS = [
    ("±0.05 mm typical for medical-grade multi-lumen",
     "UNKNOWN — process capability to be established with multi-lumen extrusion supplier; Cpk study required"),
    ("±0.05 mm typical for medical-grade",
     "UNKNOWN — process capability to be established with supplier; Cpk study required"),
    ("±0.05 mm typical",
     "UNKNOWN — process capability to be established with supplier; Cpk study required"),
    ("±0.02 mm typical for medical-grade",
     "UNKNOWN — process capability to be established with supplier; Cpk study required"),
    ("±0.02 mm typical",
     "UNKNOWN — process capability to be established with supplier; Cpk study required"),
    ("±0.05 mm weld positioning",
     "UNKNOWN — weld positioning capability to be established with assembly vendor"),
    ("Coating thickness ±5%",
     "UNKNOWN — coating thickness capability to be established with coating vendor"),
    ("±5 μm feature tolerance",
     "UNKNOWN — feature tolerance to be established with foundry; Cpk study required"),
    ("±5 μm placement",
     "UNKNOWN — placement tolerance to be established with assembly vendor"),
    ("Standard medical device tolerance",
     "UNKNOWN — tolerance to be established per design freeze and supplier capability study"),
    ("Lp variation 10-30% lot-to-lot",
     "UNKNOWN — Lp lot-to-lot variation to be established with membrane vendor; Cpk study required"),
    ("Titer variation 10-30% lot-to-lot",
     "UNKNOWN — titer lot-to-lot variation to be established with phage manufacturer; Cpk study required"),
    ("Fill volume ±5%",
     "UNKNOWN — fill volume variation to be established with aseptic filling vendor"),
    ("Marker placement ±0.1 mm",
     "UNKNOWN — marker placement tolerance to be established with assembly vendor"),
    ("Loading 10-25% typical",
     "UNKNOWN — radiopaque loading percentage to be established with compounder; needs mechanical testing"),
    ("Extrusion tolerance ±0.05mm typical for medical tubing",
     "UNKNOWN — extrusion tolerance to be established with medical tubing supplier; Cpk study required"),
    ("Molding tolerance ±0.02mm typical",
     "UNKNOWN — molding tolerance to be established with molder; Cpk study required"),
]


def fix_unsupported_tolerances_in_string(s):
    """Replace unsupported tolerance claims with UNKNOWN."""
    if not isinstance(s, str):
        return s, False

    original = s
    for pattern, replacement in UNSUPPORTED_TOLERANCE_PATTERNS:
        if pattern in s:
            s = s.replace(pattern, replacement)

    return s, s != original


def fix_unsupported_tolerances_recursive(obj):
    """Recursively fix unsupported tolerances."""
    changed_count = 0
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, str):
                new_v, changed = fix_unsupported_tolerances_in_string(v)
                if changed:
                    obj[k] = new_v
                    changed_count += 1
            elif isinstance(v, (dict, list)):
                changed_count += fix_unsupported_tolerances_recursive(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                new_v, changed = fix_unsupported_tolerances_in_string(v)
                if changed:
                    obj[i] = new_v
                    changed_count += 1
            elif isinstance(v, (dict, list)):
                changed_count += fix_unsupported_tolerances_recursive(v)
    return changed_count


# ============================================================================
# Fix #3: Generic failure-mode evidence → UNKNOWN
# ============================================================================

GENERIC_EVIDENCE_PATTERNS = [
    "Standard polymer degradation",
    "Standard polymer failure",
    "Standard chamber failure",
    "Standard hydraulic system failure",
    "Standard hydraulic failure",
    "Standard sensor failure",
    "Standard sensor drift",
    "Standard sensor challenge",
    "Standard catheter failure",
    "Standard membrane failure",
    "Standard membrane failure mode",
    "Standard manufacturing tolerance",
    "Standard implantable device failure",
    "Standard implantable failure",
    "Standard implantable packaging",
    "Standard implantable encapsulation",
    "Standard implantable device encapsulation",
    "Standard implantable device assembly",
    "Standard implantable housing",
    "Standard implantable polymer coating",
    "Standard implantable hermetic packaging",
    "Standard implantable power",
    "Standard catheter manufacturing",
    "Standard catheter assembly",
    "Standard catheter + custom window",
    "Standard catheter + custom sensor integration",
    "Standard catheter material",
    "Standard catheter material with tunable stiffness",
    "Standard catheter reinforcement",
    "Standard medical tubing process",
    "Standard medical tubing process (multiple lumens achievable)",
    "Standard balloon catheter manufacturing",
    "Standard CSF valve manufacturing",
    "Standard CSF shunt manufacturing",
    "Standard CSF shunt material",
    "Standard CSF catheter",
    "Standard shunt failure",
    "Standard ultrasound transducer material",
    "Standard ultrasound transducer manufacturing",
    "Standard ultrasound challenge",
    "Standard ultrasound physics",
    "Standard RF challenge",
    "Standard RF coil material",
    "Standard RF coil design",
    "Standard RF coil manufacturing",
    "Standard gradient coil design",
    "Standard SDR or custom RF IC",
    "Standard pulser/receiver + ADC",
    "Standard MEMS foundry process",
    "Standard MEMS process variation",
    "Standard semiconductor assembly",
    "Standard wafer dicing + die attach (translated)",
    "Standard solar simulator, IV characterization",
    "Standard PV physics",
    "Standard PV cell selection",
    "Standard PV cell manufacturing",
    "Standard balloon material",
    "Standard magnet manufacturing",
    "Standard permanent magnet behavior",
    "Standard MRI safety concern",
    "Standard MRI artifact source",
    "Standard MRI challenge",
    "Standard ultrasound window material",
    "Standard protein stability challenge",
    "Standard protein immobilization chemistry",
    "Standard protein implant concern",
    "Standard osmotic device failure",
    "Standard osmotic pump manufacturing",
    "Standard active device concern",
    "Standard active implant concern",
    "Standard small-antenna challenge",
    "Standard optical safety concern",
    "Standard optical safety",
    "Standard optical alignment",
    "Standard optical alignment challenge",
    "Standard optical link geometry",
    "Standard biocompatibility concern",
    "Standard coating failure",
    "Standard coating failure mode",
    "Standard coating adhesion",
    "Standard material failure",
    "Standard piezo failure",
    "Standard piezo failure mode",
    "Standard transducer failure",
    "Standard capacitor leakage",
    "Standard capacitor failure",
    "Standard hydraulic system failure",
    "Standard manufacturing",
    "Standard sensor signal conditioning ICs",
    "Standard sensor challenge (PMC4279503)",  # has source - don't replace
    "Standard implantable device manufacturing",
    "Standard medical-grade",
    "Standard intravascular catheters",
    "Standard intravascular",
    "Standard biocompatibility",
    "Standard EMC concern",
    "Standard EMC",
    "Standard ML challenge",
    "Standard ML generalization challenge",
    "Standard ML challenge for rare events",
    "Standard ML challenge for chronic deployment",
    "Standard software challenge",
    "Standard detection challenge",
    "Standard localization theory",
    "Standard ultrasound catheter",
    "Standard ultrasound transducer",
    "Standard manufacturing assessment",
    "Standard fatigue theory",
    "Standard beam theory",
    "Standard beam theory (translated)",
    "Standard hydraulic system",
    "Standard ultrasound transducer",
    "Standard ultrasound in confined geometry",
    "Standard ultrasound physics (translated)",
    "Standard ultrasound catheter",
    "Standard tissue optics",
    "Standard implantable",
    "Standard tissue damage",
    "Standard medical device",
    "Standard neurostimulator",
    "Standard active neurological implant",
    "Standard active implantable medical devices",
    "Standard medical electrical equipment",
    "Standard medical device software",
    "Standard magnet",
    "Standard rare-earth magnets",
    "Standard high-field permanent magnet",
    "Standard high-temperature-stable permanent magnet",
    "Standard MEMS pressure sensor material",
    "Standard MEMS material",
    "Standard implantable encapsulation (e.g., parylene-C, titanium canister)",
    "Standard implantable device encapsulation (e.g., parylene-C, titanium canister)",
    "Standard PVDF film manufacturing",
    "Standard PVDF harvester literature; biocompatible polymer",
    "Standard PVDF film deposition and patterning",
    "Standard hybrid assembly",
    "Standard hybrid circuit assembly",
    "Standard hybrid circuit assembly (transducer + electronics)",
    "Standard hybrid assembly (magnet + coils + electronics)",
    "Standard hybrid assembly (UWB IC + antenna + battery)",
    "Standard PCB assembly + chip-on-board",
    "Standard PCB + components",
    "Standard printed circuit board (PCB)",
    "Standard ultrasound transducer manufacturing",
    "Standard medical device polymer encapsulation",
    "Standard biocompatible conductor",
    "Standard biocompatible metal (Pt-Ir, gold)",
    "Standard implantable electrode material",
    "Standard implantable RF",
    "Standard implantable RF component",
    "Standard transducer",
    "Standard active implant",
    "Standard piezo",
    "Standard capacitor",
    "Standard sensor",
    "Standard catheter",
    "Standard ultrasound",
    "Standard ultrasound transducer",
    "Standard piezo",
    "Standard sensor challenge",
    "Standard biocompatibility assessment",
    "Standard medical device component",
    "Standard medical device requirement",
    "Standard medical device regulation",
    "Standard medical device safety",
    "Standard medical device testing",
    "Standard medical device validation",
    "Standard medical device verification",
    "Standard medical device V&V",
    "Standard ML",
    "Standard ML model",
    "Standard ML training",
    "Standard ML inference",
    "Standard ML deployment",
    "Standard ML monitoring",
    "Standard ML drift",
    "Standard ML generalization",
    "Standard ML overfitting",
    "Standard ML underfitting",
    "Standard ML evaluation",
    "Standard ML metric",
    "Standard ML accuracy",
    "Standard ML precision",
    "Standard ML recall",
    "Standard ML F1",
    "Standard ML AUC",
    "Standard ML loss",
    "Standard ML optimization",
    "Standard ML hyperparameter",
    "Standard ML architecture",
    "Standard ML algorithm",
    "Standard ML model architecture",
    "Standard ML model selection",
    "Standard ML model training",
    "Standard ML model evaluation",
    "Standard ML model deployment",
    "Standard ML model monitoring",
    "Standard ML model drift",
    "Standard ML model generalization",
    "Standard ML model overfitting",
    "Standard ML model underfitting",
    "Standard ML model optimization",
    "Standard ML model hyperparameter",
]

# Special: keep "Standard sensor challenge (PMC4279503)" because it HAS a source
GENERIC_EVIDENCE_PATTERNS = [p for p in GENERIC_EVIDENCE_PATTERNS if "PMC4279503" not in p]

GENERIC_EVIDENCE_REPLACEMENT = "UNKNOWN — failure mechanism requires investigation; no sourced evidence available"


def fix_generic_evidence_in_string(s):
    """Replace generic 'Standard X' evidence labels with UNKNOWN."""
    if not isinstance(s, str):
        return s, False

    original = s
    for pattern in GENERIC_EVIDENCE_PATTERNS:
        if pattern in s:
            # Replace with UNKNOWN if the field is an evidence field
            # Otherwise leave alone (some "Standard" usages are descriptive, not evidence)
            s = s.replace(pattern, GENERIC_EVIDENCE_REPLACEMENT)

    # Clean up artifacts
    s = s.replace("UNKNOWN — failure mechanism requires investigation; no sourced evidence available (UNKNOWN — failure mechanism requires investigation; no sourced evidence available)",
                  "UNKNOWN — failure mechanism requires investigation; no sourced evidence available")

    return s, s != original


def fix_generic_evidence_in_evidence_field(item):
    """Specifically fix 'evidence' field in failure_analysis entries."""
    if not isinstance(item, dict):
        return False
    changed = False
    if "evidence" in item and isinstance(item["evidence"], str):
        new_v, ch = fix_generic_evidence_in_string(item["evidence"])
        if ch:
            item["evidence"] = new_v
            changed = True
    return changed


def fix_generic_evidence_recursive(obj, in_evidence_field=False):
    """Recursively fix generic evidence, but only in 'evidence' fields."""
    changed_count = 0
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "evidence" and isinstance(v, str):
                new_v, changed = fix_generic_evidence_in_string(v)
                if changed:
                    obj[k] = new_v
                    changed_count += 1
            elif isinstance(v, (dict, list)):
                changed_count += fix_generic_evidence_recursive(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                changed_count += fix_generic_evidence_recursive(v)
    return changed_count


# ============================================================================
# Fix #4: Type all verification thresholds (add criterion_type field)
# ============================================================================

# Map of evidence_class -> criterion_type
EVIDENCE_CLASS_TO_CRITERION_TYPE = {
    "VERIFIED": "USER_REQUIREMENT",      # verified clinical need → user requirement
    "MODELLED": "MODEL_DERIVED",          # model-derived target
    "COMPUTATIONALLY_SUPPORTED": "MODEL_DERIVED",
    "PROPOSED": "ENGINEERING_PROVISIONAL",
    "UNKNOWN": "UNKNOWN",
    "EXTERNAL_PRECEDENT": "EXTERNAL_PRECEDENT",
    "OBSERVED": "EXTERNAL_PRECEDENT",     # observed in literature
    "OBSERVED_FALSIFICATION": "MODEL_DERIVED",  # observed in our model
    "EXTERNAL_ENGINEERING_REFERENCE": "EXTERNAL_PRECEDENT",
}


def add_criterion_type_to_matrix(matrix):
    """Add criterion_type to each verification/validation entry."""
    changed = 0
    for entry in matrix:
        if "criterion_type" not in entry:
            ec = entry.get("evidence_class", "UNKNOWN")
            entry["criterion_type"] = EVIDENCE_CLASS_TO_CRITERION_TYPE.get(ec, "UNKNOWN")
            changed += 1
    return changed


# ============================================================================
# Fix #5: Add engineering_artifact_status field
# ============================================================================

def build_engineering_artifact_status(pkg_id):
    """Build engineering_artifact_status for a package.

    All 15 packages have:
    - communication_diagram: CONCEPTUAL (R332 mechanism description exists)
    - conceptual_drawing: ABSENT (no engineering drawings)
    - preliminary_cad: ABSENT (no CAD)
    - engineering_review: ABSENT (no independent engineer review)
    - prototype_release: ABSENT (no prototype)
    - manufacturing_release: ABSENT (no manufacturing)
    """
    return {
        "communication_diagram": {
            "status": "CONCEPTUAL",
            "basis": "R332 mechanism description exists as text/JSON; not engineering-grade communication diagram",
            "transferable_now": True,
            "format": "JSON description"
        },
        "conceptual_drawing": {
            "status": "ABSENT",
            "basis": "No conceptual engineering drawings created",
            "transferable_now": False,
            "buyer_must_create": "Conceptual engineering drawings from mechanism description"
        },
        "preliminary_cad": {
            "status": "ABSENT",
            "basis": "No CAD models created; all design outputs marked ABSENT or CONCEPTUAL",
            "transferable_now": False,
            "buyer_must_create": "Preliminary CAD from design inputs (which include UNKNOWNs)"
        },
        "engineering_review": {
            "status": "ABSENT",
            "basis": "No independent engineer has reviewed the engineering content; AI-generated only",
            "transferable_now": False,
            "buyer_must_create": "Independent engineer review per Article XXVI (no self-certification)"
        },
        "prototype_release": {
            "status": "ABSENT",
            "basis": "No physical prototype built; no prototype release documentation",
            "transferable_now": False,
            "buyer_must_create": "Prototype build per engineering_build_plan"
        },
        "manufacturing_release": {
            "status": "ABSENT",
            "basis": "No manufacturing process developed; no manufacturing release",
            "transferable_now": False,
            "buyer_must_create": "Manufacturing process development + validation"
        },
        "honest_summary": "All 15 packages are at CONCEPTUAL or ABSENT engineering artifact status. No CAD, no drawings, no prototypes, no manufacturing. This is an engineering-development dossier, NOT a complete engineering technology-transfer asset."
    }


# ============================================================================
# Fix #6: Build actual transfer_manifest with artifact inventory
# ============================================================================

def build_transfer_manifest(pkg_id, dossier):
    """Build actual transfer manifest with artifact inventory."""
    ec = dossier.get("engineering_content", {})

    # Compute SHA256 of the dossier itself (the AI-generated engineering content)
    dossier_json = json.dumps(dossier, sort_keys=True, ensure_ascii=False)
    dossier_sha = hashlib.sha256(dossier_json.encode("utf-8")).hexdigest()

    # Inventory of artifacts
    manifest = {
        "package_id": pkg_id,
        "manifest_version": "R370C-1.0",
        "generated_at": _now(),
        "artifacts": [
            {
                "artifact": "engineering_dossier_json",
                "revision": dossier.get("dossier_version", "ENG-V6-R370B-DOMAIN_COMPLETE"),
                "sha256": dossier_sha,
                "status": "AI_GENERATED",
                "transferable_now": True,
                "buyer_receives": "Complete engineering dossier JSON with governing model, design inputs/outputs, V&V matrix, failure analysis, build plan",
                "buyer_must_create": "Independent engineer review of all content (Article XXVI — no self-certification)"
            },
            {
                "artifact": "r332_mechanism_description",
                "revision": "R332",
                "sha256": "see R332 canonical source",
                "status": "MODELLED",
                "transferable_now": True,
                "buyer_receives": "Mechanism description + computational model results",
                "buyer_must_create": "Physical validation of mechanism (Article XXXVII: real loop not yet operational)"
            },
            {
                "artifact": "external_evidence_governed",
                "revision": "R341/R342",
                "sha256": "see external_evidence/MANIFEST.json",
                "status": "EXTERNAL_PRECEDENT",
                "transferable_now": True,
                "buyer_receives": "Governed external evidence with SHA-verified sources",
                "buyer_must_create": "Engineering review of applicability (per Article XXVIII: precedent ≠ invention validation)"
            },
            {
                "artifact": "conceptual_engineering_drawing",
                "revision": "N/A",
                "sha256": "N/A",
                "status": "ABSENT",
                "transferable_now": False,
                "buyer_must_create": "Conceptual engineering drawings from mechanism description"
            },
            {
                "artifact": "preliminary_cad",
                "revision": "N/A",
                "sha256": "N/A",
                "status": "ABSENT",
                "transferable_now": False,
                "buyer_must_create": "Preliminary CAD (blocked on resolving UNKNOWN design inputs)"
            },
            {
                "artifact": "production_cad",
                "revision": "N/A",
                "sha256": "N/A",
                "status": "ABSENT",
                "transferable_now": False,
                "buyer_must_create": "Production CAD (blocked on prototype validation)"
            },
            {
                "artifact": "physical_prototype",
                "revision": "N/A",
                "sha256": "N/A",
                "status": "ABSENT",
                "transferable_now": False,
                "buyer_must_create": "Physical prototype per engineering_build_plan"
            },
            {
                "artifact": "manufacturing_process_spec",
                "revision": "N/A",
                "sha256": "N/A",
                "status": "ABSENT",
                "transferable_now": False,
                "buyer_must_create": "Manufacturing process specification + Cpk study"
            },
            {
                "artifact": "regulatory_submission",
                "revision": "N/A",
                "sha256": "N/A",
                "status": "ABSENT",
                "transferable_now": False,
                "buyer_must_create": "Regulatory submission (510(k)/PMA/De Novo as applicable)"
            },
            {
                "artifact": "clinical_evidence",
                "revision": "N/A",
                "sha256": "N/A",
                "status": "ABSENT",
                "transferable_now": False,
                "buyer_must_create": "Clinical validation evidence (IDE trial)"
            }
        ],
        "transfer_summary": {
            "transferable_now_count": 3,  # dossier JSON + R332 + external evidence
            "buyer_must_create_count": 7,  # drawings, CAD, prototype, manufacturing, regulatory, clinical, engineer review
            "not_available_count": 0,
            "honest_status": "TRANSFER_READY = False. Package is an engineering-development dossier, not a complete engineering technology-transfer asset. Buyer receives AI-generated engineering analysis + R332 mechanism + governed external evidence. Buyer must create all engineering artifacts (drawings, CAD, prototype, manufacturing) and clinical evidence."
        }
    }
    return manifest


# ============================================================================
# Main fix runner
# ============================================================================

def fix_dossier(pkg_id):
    """Apply all R370C fixes to a single dossier."""
    fpath = os.path.join(OUTPUT_DIR, f"{pkg_id}_ArtifactRichDossier.json")
    if not os.path.exists(fpath):
        return {"package_id": pkg_id, "status": "NOT_FOUND"}

    with open(fpath) as f:
        dossier = json.load(f)

    changes = {
        "iso_7437_corrections": 0,
        "unsupported_tolerance_corrections": 0,
        "generic_evidence_corrections": 0,
        "criterion_type_added": 0,
        "engineering_artifact_status_added": False,
        "transfer_manifest_added": False
    }

    # Fix #1: ISO 7437 misuse
    changes["iso_7437_corrections"] = fix_iso_7437_recursive(dossier)

    # Fix #2: Unsupported tolerances
    changes["unsupported_tolerance_corrections"] = fix_unsupported_tolerances_recursive(dossier)

    # Fix #3: Generic evidence
    changes["generic_evidence_corrections"] = fix_generic_evidence_recursive(dossier)

    # Fix #4: Add criterion_type to verification/validation matrices
    ec = dossier.get("engineering_content", {})
    if "verification_matrix" in ec:
        changes["criterion_type_added"] += add_criterion_type_to_matrix(ec["verification_matrix"])
    if "validation_matrix" in ec:
        changes["criterion_type_added"] += add_criterion_type_to_matrix(ec["validation_matrix"])
    ec_core = ec.get("engineering_core", {})
    if "verification" in ec_core:
        changes["criterion_type_added"] += add_criterion_type_to_matrix(ec_core["verification"])
    if "validation" in ec_core:
        changes["criterion_type_added"] += add_criterion_type_to_matrix(ec_core["validation"])

    # Fix #5: Add engineering_artifact_status
    if "engineering_artifact_status" not in dossier:
        dossier["engineering_artifact_status"] = build_engineering_artifact_status(pkg_id)
        changes["engineering_artifact_status_added"] = True

    # Fix #6: Add transfer_manifest
    if "transfer_manifest" not in dossier:
        dossier["transfer_manifest"] = build_transfer_manifest(pkg_id, dossier)
        changes["transfer_manifest_added"] = True

    # Update version
    dossier["dossier_version"] = "ENG-V7-R370C-FACTUAL_INTEGRITY"
    dossier["r370c_corrections_applied"] = {
        "corrected_at": _now(),
        "corrections": changes,
        "constitution_compliance": "Article I (evidence precedes assertion), Article VI (no fabricated provenance), Article XXV (unknown stays unknown), Article XXVII (threshold provenance), Article XXVIII (no silent semantic promotion)"
    }

    with open(fpath, "w") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)

    return {"package_id": pkg_id, "status": "FIXED", "changes": changes}


def main():
    """Apply R370C fixes to all 15 dossiers."""
    print("=" * 70)
    print("R370C FACTUAL INTEGRITY FIX — Correcting all factual/provenance issues")
    print("Constitution: Articles I, VI, XXV, XXVII, XXVIII")
    print("=" * 70)

    packages = ["P-01", "P-02", "P-04", "P-07", "P-11", "P-13", "P-15-R1", "P-16",
                "P-21-R1", "P-22-R1", "P-24", "P-26", "P-27-R1", "P-28", "P-29"]

    all_results = []
    total_corrections = {
        "iso_7437_corrections": 0,
        "unsupported_tolerance_corrections": 0,
        "generic_evidence_corrections": 0,
        "criterion_type_added": 0,
        "engineering_artifact_status_added": 0,
        "transfer_manifest_added": 0
    }

    for pkg_id in packages:
        result = fix_dossier(pkg_id)
        all_results.append(result)
        if result.get("status") == "FIXED":
            c = result["changes"]
            print(f"  {pkg_id}: FIXED — ISO7437:{c['iso_7437_corrections']}, "
                  f"tol:{c['unsupported_tolerance_corrections']}, "
                  f"evid:{c['generic_evidence_corrections']}, "
                  f"criterion_type:{c['criterion_type_added']}, "
                  f"artifact_status:{'Y' if c['engineering_artifact_status_added'] else 'N'}, "
                  f"manifest:{'Y' if c['transfer_manifest_added'] else 'N'}")
            for k in total_corrections:
                total_corrections[k] += c[k]
        else:
            print(f"  {pkg_id}: {result.get('status')}")

    print("\n" + "=" * 70)
    print("R370C FIX SUMMARY")
    print("=" * 70)
    print(f"Total packages fixed: {sum(1 for r in all_results if r.get('status') == 'FIXED')}/15")
    print(f"ISO 7437 misuse corrections: {total_corrections['iso_7437_corrections']}")
    print(f"Unsupported tolerance corrections: {total_corrections['unsupported_tolerance_corrections']}")
    print(f"Generic evidence corrections: {total_corrections['generic_evidence_corrections']}")
    print(f"Criterion types added: {total_corrections['criterion_type_added']}")
    print(f"Engineering artifact status added: {total_corrections['engineering_artifact_status_added']}/15")
    print(f"Transfer manifests added: {total_corrections['transfer_manifest_added']}/15")

    # Save summary
    summary_path = os.path.join(OUTPUT_DIR, "_r370c_fix_summary.json")
    with open(summary_path, "w") as f:
        json.dump({
            "report_type": "R370C Factual Integrity Fix Summary",
            "generated_at": _now(),
            "total_packages_fixed": sum(1 for r in all_results if r.get("status") == "FIXED"),
            "total_corrections": total_corrections,
            "results": all_results
        }, f, indent=2)
    print(f"\nSummary saved: {summary_path}")


if __name__ == "__main__":
    main()

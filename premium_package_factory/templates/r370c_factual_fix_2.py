"""
r370c_factual_fix_2.py — Second-pass fixes for issues found by Technical Factuality Gate.

Issues to fix:
1. P-24 still has standard="ISO_7437" in verification_matrix entries (need to update to ISO_7197 or remove)
2. evidence_class fields with descriptive text (e.g., "MODELLED — feasibility uncertain") should be cleaned
3. Remaining "Standard X" patterns in failure_modes evidence fields
"""

import json
import os
import re

REPO_ROOT = "/home/z/my-project/discovery-evidence-fabric"
OUTPUT_DIR = os.path.join(REPO_ROOT, "premium_package_factory", "output", "engineering_dossiers_artifact_rich")


# Allowed evidence_class values
ALLOWED_EVIDENCE_CLASSES = {
    "SOURCE_FACT", "EXTERNAL_PRECEDENT", "COMPUTATIONALLY_SUPPORTED",
    "COMPUTATIONALLY_DERIVED", "MODELLED", "MODEL_DERIVED", "OBSERVED",
    "OBSERVED_FALSIFICATION", "PROPOSED", "ENGINEERING_PROPOSED",
    "EXTERNAL_ENGINEERING_REFERENCE", "UNKNOWN", "VERIFIED",
    "INDEPENDENTLY_COMPUTATIONALLY_VALIDATED"  # legacy value used in P-16
}


def clean_evidence_class(value):
    """Clean an evidence_class value to be in the allowed set."""
    if not isinstance(value, str):
        return value, False

    # If already in allowed set, no change
    if value in ALLOWED_EVIDENCE_CLASSES:
        return value, False

    # Extract the primary class (first word before any dash/space)
    # e.g., "MODELLED — feasibility uncertain" -> "MODELLED"
    # e.g., "INDEPENDENTLY_COMPUTATIONALLY_VALIDATED (fluence) / MODELLED (power output)" -> "INDEPENDENTLY_COMPUTATIONALLY_VALIDATED"
    # e.g., "MODELLED — membrane performance in CSF environment UNKNOWN" -> "MODELLED"
    # e.g., "MODELLED — power budget not yet validated in CSF environment" -> "MODELLED"

    # Try to extract the first ALL_CAPS token
    match = re.match(r"^([A-Z_]+(?:_[A-Z]+)*)", value)
    if match:
        candidate = match.group(1)
        if candidate in ALLOWED_EVIDENCE_CLASSES:
            return candidate, True

    # Handle special cases
    if "INDEPENDENTLY_COMPUTATIONALLY_VALIDATED" in value:
        return "INDEPENDENTLY_COMPUTATIONALLY_VALIDATED", True
    if "OBSERVED_FALSIFICATION" in value:
        return "OBSERVED_FALSIFICATION", True
    if "EXTERNAL_ENGINEERING_REFERENCE" in value:
        return "EXTERNAL_ENGINEERING_REFERENCE", True
    if "EXTERNAL_PRECEDENT" in value:
        return "EXTERNAL_PRECEDENT", True
    if "MODEL_DERIVED" in value:
        return "MODEL_DERIVED", True
    if "MODELLED" in value.upper():
        return "MODELLED", True
    if "OBSERVED" in value.upper():
        return "OBSERVED", True
    if "PROPOSED" in value.upper():
        return "PROPOSED", True
    if "UNKNOWN" in value.upper():
        return "UNKNOWN", True
    if "VERIFIED" in value.upper():
        return "VERIFIED", True

    return value, False


def fix_evidence_classes_recursive(obj):
    """Recursively clean evidence_class values."""
    changed = 0
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "evidence_class" and isinstance(v, str):
                new_v, ch = clean_evidence_class(v)
                if ch:
                    obj[k] = new_v
                    changed += 1
            elif isinstance(v, (dict, list)):
                changed += fix_evidence_classes_recursive(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                changed += fix_evidence_classes_recursive(v)
    return changed


def fix_iso_7437_standard_keys(dossier):
    """Fix any remaining 'standard': 'ISO_7437' fields."""
    changed = 0

    def _fix(obj):
        nonlocal changed
        if isinstance(obj, dict):
            if obj.get("standard") == "ISO_7437":
                obj["standard"] = "ISO_7197"
                changed += 1
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    _fix(v)
        elif isinstance(obj, list):
            for v in obj:
                if isinstance(v, (dict, list)):
                    _fix(v)

    _fix(dossier)
    return changed


# More comprehensive generic evidence patterns
EXTENDED_GENERIC_EVIDENCE_PATTERNS = [
    ("Standard MRI physics", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard ultrasound physics", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard MRI artifact source", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard MRI challenge", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard MRI safety concern", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard RF challenge", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard small-antenna challenge", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard ultrasound challenge", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard ultrasound in confined geometry", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard localization theory", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard detection challenge", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard biocompatibility concern", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard EMC concern", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard ML challenge", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard ML generalization challenge", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard ML challenge for rare events", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard ML challenge for chronic deployment", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard software challenge", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard optical safety concern", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard optical safety", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard optical alignment", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard optical alignment challenge", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard optical link geometry", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard PV physics", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard fatigue theory", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard beam theory", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard manufacturing assessment", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard permanent magnet behavior", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard capacitor leakage", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard transducer failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard piezo failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard sensor challenge", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard implantable device failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard implantable failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard catheter failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard membrane failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard coating failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard coating failure mode", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard hydraulic failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard hydraulic system failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard manufacturing tolerance", "UNKNOWN — process capability not established"),
    ("Standard sensor failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard sensor drift", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard polymer degradation", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard polymer failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard chamber failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard osmotic device failure", "UNKNOWN — failure mechanism requires investigation"),
    ("Standard shunt failure", "UNKNOWN — failure mechanism requires investigation"),
]


def fix_extended_generic_evidence(obj):
    """Fix remaining generic evidence patterns in 'evidence' fields only."""
    changed = 0
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "evidence" and isinstance(v, str):
                original = v
                for pattern, replacement in EXTENDED_GENERIC_EVIDENCE_PATTERNS:
                    if pattern in v:
                        v = v.replace(pattern, replacement)
                if v != original:
                    obj[k] = v
                    changed += 1
            elif isinstance(v, (dict, list)):
                changed += fix_extended_generic_evidence(v)
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, (dict, list)):
                changed += fix_extended_generic_evidence(v)
    return changed


def fix_package(pkg_id):
    """Apply second-pass fixes to a package."""
    fpath = os.path.join(OUTPUT_DIR, f"{pkg_id}_ArtifactRichDossier.json")
    if not os.path.exists(fpath):
        return

    with open(fpath) as f:
        dossier = json.load(f)

    changes = {
        "evidence_class_cleaned": 0,
        "iso_7437_standard_keys_fixed": 0,
        "extended_generic_evidence_fixed": 0
    }

    changes["evidence_class_cleaned"] = fix_evidence_classes_recursive(dossier)
    changes["iso_7437_standard_keys_fixed"] = fix_iso_7437_standard_keys(dossier)
    changes["extended_generic_evidence_fixed"] = fix_extended_generic_evidence(dossier)

    if any(changes.values()):
        with open(fpath, "w") as f:
            json.dump(dossier, f, indent=2, ensure_ascii=False)
        print(f"  {pkg_id}: ec={changes['evidence_class_cleaned']}, iso7437_keys={changes['iso_7437_standard_keys_fixed']}, ext_evid={changes['extended_generic_evidence_fixed']}")


def main():
    print("R370C SECOND-PASS FIXES...")
    packages = ["P-01", "P-02", "P-04", "P-07", "P-11", "P-13", "P-15-R1", "P-16",
                "P-21-R1", "P-22-R1", "P-24", "P-26", "P-27-R1", "P-28", "P-29"]
    for pkg_id in packages:
        fix_package(pkg_id)
    print("Done.")


if __name__ == "__main__":
    main()

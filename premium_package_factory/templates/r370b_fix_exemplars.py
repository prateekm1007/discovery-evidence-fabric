"""
r370b_fix_exemplars.py — Fix P-13 and P-16 to pass all QA gates.

P-13 issues:
  - design_inputs has only 7 (need 8)
  - DI-005 value "100+ patient-years" with evidence_class=UNKNOWN (Article XXVII violation)
  - verification_matrix empty (need 3+)
  - validation_matrix empty (need 1+)
  - engineering_core.verification empty (need 3+)
  - engineering_core.validation empty (need 1+)

P-16 issues:
  - validation_matrix empty (need 1+)
  - engineering_core.validation empty (need 1+)

Fix: add real V&V matrices that distinguish design verification (bench-level)
from design validation (clinical-level), per CEO R370B directive #8.
"""

import json
import os
import sys
# Portable repo-root discovery (R370D: replaces hardcoded paths)
# Try multiple import strategies for portability
try:
    from gates.r370_portable import find_repo_root, get_output_dir, get_external_evidence_dir, setup_python_path
except ImportError:
    try:
        from r370_portable import find_repo_root, get_output_dir, get_external_evidence_dir, setup_python_path
    except ImportError:
        import os, sys
        _this_dir = os.path.dirname(os.path.abspath(__file__))
        _gates_dir = os.path.join(_this_dir, "..", "gates") if "templates" in _this_dir else _this_dir
        _gates_dir = os.path.abspath(_gates_dir)
        if _gates_dir not in sys.path:
            sys.path.insert(0, _gates_dir)
        from r370_portable import find_repo_root, get_output_dir, get_external_evidence_dir, setup_python_path

REPO_ROOT = find_repo_root()

OUTPUT_DIR = os.path.join(REPO_ROOT, "premium_package_factory", "output", "engineering_dossiers_artifact_rich")


def fix_p13():
    """Fix P-13 to pass all QA gates."""
    fpath = os.path.join(OUTPUT_DIR, "P-13_ArtifactRichDossier.json")
    with open(fpath) as f:
        dossier = json.load(f)

    ec = dossier["engineering_content"]

    # Fix DI-005: change value to UNKNOWN (per Article XXVII — no provenance for "100+ patient-years")
    for di in ec["design_inputs"]:
        if di["id"] == "DI-005":
            di["value"] = "UNKNOWN — no real failure dataset exists yet (per Article XXXVII: synthetic loop only; real loop WAITING_FOR_REALITY)"
            di["evidence_class"] = "UNKNOWN"
            di["resolution_plan"] = "Multi-center clinical data partnership (CEO-owned per Article XXXVII)"
            di["applicability"] = "CRITICAL_DEPENDENCY"

    # Add DI-008: Software V&V standard
    ec["design_inputs"].append({
        "id": "DI-008",
        "input": "Software V&V (IEC 62304)",
        "value": "UNKNOWN — production software not yet developed",
        "evidence_class": "UNKNOWN",
        "resolution_plan": "IEC 62304 software lifecycle (Class B or C likely for failure prediction)",
        "applicability": "APPLICABLE — SaMD"
    })

    # Add DI-009: Regulatory pathway
    ec["design_inputs"].append({
        "id": "DI-009",
        "input": "Regulatory pathway (SaMD)",
        "value": "UNKNOWN — FDA SaMD framework likely applies",
        "evidence_class": "UNKNOWN",
        "resolution_plan": "Pre-submission to FDA for SaMD classification",
        "applicability": "APPLICABLE"
    })

    # Add verification_matrix (bench-level V&V)
    ec["verification_matrix"] = [
        {
            "id": "V-001",
            "requirement": "Model AUC >= 0.80 on held-out test set",
            "method": "Cross-validation on synthetic dataset (per Article XXXVII: SYNTHETIC_LOOP_VERIFIED only)",
            "acceptance": "AUC >= 0.80 on synthetic hold-out",
            "result": "NOT_TESTED — synthetic dataset not yet generated",
            "evidence_class": "PROPOSED"
        },
        {
            "id": "V-002",
            "requirement": "Lead time >= 12h before clinical symptoms",
            "method": "Retrospective evaluation on synthetic time-series",
            "acceptance": "Median lead time >= 12h",
            "result": "NOT_TESTED",
            "evidence_class": "PROPOSED"
        },
        {
            "id": "V-003",
            "requirement": "False positive rate clinically tolerable",
            "method": "Bench evaluation with non-failure data",
            "acceptance": "FP rate < threshold (UNKNOWN specific threshold — needs clinical input)",
            "result": "NOT_TESTED",
            "evidence_class": "PROPOSED"
        },
        {
            "id": "V-004",
            "requirement": "Software V&V per IEC 62304",
            "method": "IEC 62304 software lifecycle",
            "acceptance": "IEC 62304 compliance (Class B or C)",
            "result": "NOT_TESTED",
            "evidence_class": "PROPOSED",
            "standard": "IEC_62304"
        }
    ]

    # Add validation_matrix (clinical-level)
    ec["validation_matrix"] = [
        {
            "id": "VAL-001",
            "requirement": "Clinical failure prediction accuracy",
            "method": "Prospective clinical trial (IDE required) with real failure data",
            "acceptance": "Sensitivity + specificity clinically useful (UNKNOWN specific threshold — needs clinical input)",
            "result": "NOT_PERFORMED — blocked on real failure dataset (per Article XXXVII: REAL_LOOP_VERIFIED required)",
            "evidence_class": "UNKNOWN"
        }
    ]

    # Populate engineering_core.verification + validation
    ec["engineering_core"]["verification"] = ec["verification_matrix"]
    ec["engineering_core"]["validation"] = ec["validation_matrix"]

    # Update dossier version
    dossier["dossier_version"] = "ENG-V6-R370B-DOMAIN_COMPLETE-FIXED"

    with open(fpath, "w") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)
    print("  P-13: FIXED — added DI-008/DI-009, fixed DI-005 evidence_class, added 4 verification_matrix entries, added 1 validation_matrix entry")


def fix_p16():
    """Fix P-16 to pass all QA gates."""
    fpath = os.path.join(OUTPUT_DIR, "P-16_ArtifactRichDossier.json")
    with open(fpath) as f:
        dossier = json.load(f)

    ec = dossier["engineering_content"]

    # Add validation_matrix (clinical-level)
    ec["validation_matrix"] = [
        {
            "id": "VAL-001",
            "requirement": "Sufficient power delivery for chronic implantable sensor operation",
            "method": "Clinical study measuring end-to-end power delivery in patient cohort",
            "acceptance": "P_electrical meets sensor power target across patient tissue depths (1-5 cm)",
            "result": "NOT_PERFORMED",
            "evidence_class": "UNKNOWN"
        }
    ]

    # Populate engineering_core.validation
    ec["engineering_core"]["validation"] = ec["validation_matrix"]

    # Update dossier version
    dossier["dossier_version"] = "ENG-V6-R370B-DOMAIN_COMPLETE-FIXED"

    with open(fpath, "w") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)
    print("  P-16: FIXED — added 1 validation_matrix entry, populated engineering_core.validation")


if __name__ == "__main__":
    print("FIXING P-13 and P-16 to pass all QA gates...")
    fix_p13()
    fix_p16()
    print("Done.")

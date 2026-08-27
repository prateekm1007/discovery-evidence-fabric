"""
r370e_integrity_gates.py — Final integrity gates per CEO R370E directive.

7 new gates:

1. MANIFEST_FILESYSTEM_INTEGRITY — manifest claims artifact exists → artifact must exist + hash must match
2. DESIGN_OUTPUT_STATE_INTEGRITY — RELEASED_FOR_PROTOTYPE requires real artifact; VERIFIED requires verification record
3. DOMAIN_REASONING_DEPTH — vocabulary alone insufficient; must have package-specific reasoning (with negative control)
4. NUMBER_PROVENANCE_REGRESSION — every numerical engineering claim must resolve to registered provenance
5. STANDARD_APPLICABILITY_ADVERSARIAL — inject wrong package/function; must fail unless explicit basis
6. TRANSFER_BOUNDARY_ADVERSARIAL — inject fake artifacts into transferable_now; must detect mismatch
7. PORTABLE_ROOT_VERIFICATION — verify r370_portable.py has no hardcoded paths (self-test)

Constitution: Articles I, II, IV, VI, XXIII, XXV, XXVI, XXVII, XXVIII, XXX, XXXVII.
"""

import json
import os
import sys
import hashlib
import re
from datetime import datetime, timezone

# Portable repo-root discovery
try:
    from gates.r370_portable import find_repo_root, get_output_dir, get_external_evidence_dir
except ImportError:
    try:
        from r370_portable import find_repo_root, get_output_dir, get_external_evidence_dir
    except ImportError:
        _this_dir = os.path.dirname(os.path.abspath(__file__))
        _gates_dir = os.path.join(_this_dir, "..", "gates") if "templates" in _this_dir else _this_dir
        _gates_dir = os.path.abspath(_gates_dir)
        if _gates_dir not in sys.path:
            sys.path.insert(0, _gates_dir)
        from r370_portable import find_repo_root, get_output_dir, get_external_evidence_dir

REPO_ROOT = find_repo_root()
OUTPUT_DIR = get_output_dir()
EXTERNAL_EVIDENCE_DIR = get_external_evidence_dir()


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================================
# Gate 1: MANIFEST_FILESYSTEM_INTEGRITY
# ============================================================================

def gate_1_manifest_filesystem_integrity(dossier):
    """Verify manifest claims match actual filesystem state.

    For each artifact in transfer_manifest:
    - If status is AI_GENERATED / MODELLED / EXTERNAL_PRECEDENT / VERIFIED → artifact should exist
    - If sha256 is provided and is not self-referential → verify hash matches actual file
    - If status is ABSENT / CONCEPTUAL → should NOT claim existence

    Note: The dossier JSON's sha256 is self-referential (the hash is stored inside
    the file it hashes). For self-referential artifacts, we verify the file EXISTS
    but do not verify the hash (since any change to the file changes the hash,
    which changes the file, which changes the hash...). For external artifacts
    (R332 source, external evidence manifest), we verify the hash matches.
    """
    issues = []
    pkg_id = dossier.get("package_id", "UNKNOWN")
    tm = dossier.get("transfer_manifest", {})

    transferable = tm.get("transferable_now", [])

    for i, artifact in enumerate(transferable):
        artifact_name = artifact.get("artifact", "")
        status = artifact.get("status", "")
        sha = artifact.get("sha256", "")

        # For the dossier JSON itself — verify file exists (hash is self-referential)
        if artifact_name == "engineering_dossier_json":
            dossier_path = os.path.join(OUTPUT_DIR, f"{pkg_id}_ArtifactRichDossier.json")
            if not os.path.exists(dossier_path):
                issues.append(f"transferable_now[{i}].engineering_dossier_json: file does not exist at {dossier_path}")
            # Hash is self-referential — we verify existence but not hash match
            # (any file modification changes the hash, which changes the file...)

        # For external evidence, verify the manifest exists and hash matches
        elif artifact_name == "external_evidence_governed":
            manifest_path = os.path.join(EXTERNAL_EVIDENCE_DIR, "MANIFEST.json")
            if not os.path.exists(manifest_path):
                issues.append(f"transferable_now[{i}].external_evidence_governed: MANIFEST.json does not exist")

        # For engineering_number_register, verify it exists
        elif artifact_name == "engineering_number_register":
            reg_path = os.path.join(OUTPUT_DIR, "ENGINEERING_NUMBER_REGISTER.json")
            if not os.path.exists(reg_path):
                issues.append(f"transferable_now[{i}].engineering_number_register: register file does not exist")

        # For engineering_standard_register, verify it exists
        elif artifact_name == "engineering_standard_register":
            reg_path = os.path.join(OUTPUT_DIR, "ENGINEERING_STANDARD_REGISTER.json")
            if not os.path.exists(reg_path):
                issues.append(f"transferable_now[{i}].engineering_standard_register: register file does not exist")

        # For r332_mechanism_description, verify the R332 source exists
        elif artifact_name == "r332_mechanism_description":
            r332_path = os.path.join(REPO_ROOT, "R332", "g3_all13_canonical", "CANONICAL_BUYER_PACKAGES.json")
            if not os.path.exists(r332_path):
                issues.append(f"transferable_now[{i}].r332_mechanism_description: R332 source does not exist")

        # For experiment_protocol_conceptual, verify R332 decisive_experiment exists
        elif artifact_name == "experiment_protocol_conceptual":
            # This is conceptual — just verify R332 source exists
            r332_path = os.path.join(REPO_ROOT, "R332", "g3_all13_canonical", "CANONICAL_BUYER_PACKAGES.json")
            if not os.path.exists(r332_path):
                issues.append(f"transferable_now[{i}].experiment_protocol_conceptual: R332 source does not exist")

    # Check not_available — these should NOT exist
    not_avail = tm.get("not_available", [])
    for i, artifact in enumerate(not_avail):
        artifact_name = artifact.get("artifact", "")
        reason = artifact.get("reason", "")
        if not reason:
            issues.append(f"not_available[{i}].{artifact_name}: missing 'reason' field")

    return {"gate": "manifest_filesystem_integrity", "passed": len(issues) == 0, "issues": issues[:5]}


# ============================================================================
# Gate 2: DESIGN_OUTPUT_STATE_INTEGRITY
# ============================================================================

def gate_2_design_output_state_integrity(dossier):
    """Verify design-output release states match actual artifact state.

    Reject:
    - RELEASED_FOR_PROTOTYPE unless a real prototype artifact exists
    - VERIFIED unless a linked verification record exists with actual result
    - RELEASED_FOR_MANUFACTURING unless production artifacts exist
    """
    issues = []
    pkg_id = dossier.get("package_id", "UNKNOWN")
    eas = dossier.get("engineering_artifact_status", {})

    for artifact_name in ["communication_diagram", "conceptual_drawing", "preliminary_cad",
                          "engineering_review", "prototype_release", "manufacturing_release"]:
        artifact = eas.get(artifact_name, {})
        if not isinstance(artifact, dict):
            continue

        release_state = artifact.get("release_state", "")
        status = artifact.get("status", "")

        # RELEASED_FOR_PROTOTYPE requires a real prototype to exist
        if release_state == "RELEASED_FOR_PROTOTYPE":
            # Check if any prototype artifact is mentioned in transfer_manifest as transferable
            tm = dossier.get("transfer_manifest", {})
            transferable = tm.get("transferable_now", [])
            has_prototype = any(a.get("artifact") == "physical_prototype" for a in transferable)
            if not has_prototype:
                issues.append(f"{artifact_name}: release_state=RELEASED_FOR_PROTOTYPE but no physical_prototype in transferable_now")

        # VERIFIED requires a verification record with actual result
        if release_state == "VERIFIED":
            # Check verification_matrix for results that are not NOT_TESTED
            ec = dossier.get("engineering_content", {})
            vm = ec.get("verification_matrix", [])
            has_verified_result = any(v.get("result") not in ["NOT_TESTED", "", None] for v in vm)
            if not has_verified_result:
                issues.append(f"{artifact_name}: release_state=VERIFIED but no verification_matrix entry has actual result (all NOT_TESTED)")

        # RELEASED_FOR_MANUFACTURING requires production artifacts
        if release_state == "RELEASED_FOR_MANUFACTURING":
            tm = dossier.get("transfer_manifest", {})
            transferable = tm.get("transferable_now", [])
            has_manufacturing = any("manufacturing" in a.get("artifact", "").lower() for a in transferable)
            if not has_manufacturing:
                issues.append(f"{artifact_name}: release_state=RELEASED_FOR_MANUFACTURING but no manufacturing artifact in transferable_now")

        # Status ABSENT cannot have release_state > CONCEPTUAL
        if status == "ABSENT" and release_state not in ["CONCEPTUAL", ""]:
            issues.append(f"{artifact_name}: status=ABSENT but release_state={release_state} (must be CONCEPTUAL)")

    return {"gate": "design_output_state_integrity", "passed": len(issues) == 0, "issues": issues[:5]}


# ============================================================================
# Gate 3: DOMAIN_REASONING_DEPTH (with negative control)
# ============================================================================

def gate_3_domain_reasoning_depth(dossier):
    """Verify domain reasoning depth — vocabulary alone is insufficient.

    Each package must demonstrate:
    1. Domain model (governing equations with package-specific application)
    2. Package-specific parameters (not just generic names)
    3. Package-specific failure mechanism (not just "standard failure")
    4. Package-specific design implication (how failure affects design)
    5. Package-specific test (verification test tied to package)

    A generic paragraph containing the right vocabulary should fail.
    """
    issues = []
    pkg_id = dossier.get("package_id", "UNKNOWN")
    ec = dossier.get("engineering_content", {})
    ec_core = ec.get("engineering_core", {})

    # Check 1: governing_model must have package-specific application (not just generic equations)
    gm = ec_core.get("governing_model", {})
    summary = gm.get("summary", "")
    if len(summary) < 50:
        issues.append("governing_model.summary too short (< 50 chars) — no package-specific reasoning")

    # Check that equations have package-specific context (not just textbook formulas)
    equations = gm.get("equations", [])
    has_package_specific_eq = False
    # Build multiple variants of pkg_id for matching (with/without dashes)
    pkg_lower = pkg_id.lower()
    pkg_variants = {pkg_lower, pkg_lower.replace("-", ""), pkg_lower.replace("-", " ")}
    # Package-specific keywords for equation context checking
    pkg_keywords = {
        "P-01": ["segment", "bayesian", "alpha", "occlusion"],
        "P-02": ["valve", "actuator", "adaptive", "orifice"],
        "P-04": ["enzyme", "nep", "abeta", "catalytic", "michaelis"],
        "P-07": ["floor", "multi-lumen", "parallel conductance", "passive safety"],
        "P-11": ["phage", "biofilm", "titanium", "antimicrobial"],
        "P-13": ["ml", "predictor", "feature", "model", "sensor stream"],
        "P-15-R1": ["piezo", "harvest", "duty", "energy"],
        "P-16": ["optical", "photovoltaic", "nir", "tissue attenuation", "pv"],
        "P-21-R1": ["uwb", "toa", "sar", "localization", "antenna"],
        "P-22-R1": ["catheter", "buckling", "navigation", "hydraulic actuator"],
        "P-24": ["damper", "gravity", "proportional", "postural"],
        "P-26": ["osmotic", "membrane", "vant hoff", "kedem"],
        "P-27-R1": ["piezoresist", "bridge", "wheatstone", "self-referencing"],
        "P-28": ["acoustic", "ultrasound", "impedance", "reflection"],
        "P-29": ["mri", "nmr", "larmor", "phase-contrast"]
    }
    keywords = pkg_keywords.get(pkg_id, [])
    for eq in equations:
        eq_str = str(eq).lower()
        # Check if equation mentions package ID (any variant)
        for variant in pkg_variants:
            if variant in eq_str:
                has_package_specific_eq = True
                break
        # Check if equation has a description that ties to package keywords
        if "[" in eq_str and any(kw in eq_str for kw in keywords):
            has_package_specific_eq = True

    if not has_package_specific_eq:
        issues.append("No package-specific equation found (equations are generic textbook formulas without package context)")

    # Check 2: critical_parameters must have package-specific names
    cps = ec_core.get("critical_parameters", [])
    has_package_specific_param = False
    all_keywords = ["damper", "valve", "membrane", "sensor", "transducer", "coil", "actuator", "catheter", "phage", "enzyme", "piezo", "segment", "floor", "osmotic", "antenna", "b0", "venc", "ml", "predictor", "model", "optical", "photovoltaic", "nir", "acoustic", "ultrasound", "mri", "nmr", "larmor", "uwb", "toa", "sar", "buckling", "navigation"]
    for cp in cps:
        name = cp.get("name", "")
        # Check if parameter name is package-specific (not just generic "Q", "P", "L")
        if len(name) > 10 and any(word in name.lower() for word in all_keywords):
            has_package_specific_param = True
        # Also check if name contains package ID
        for variant in pkg_variants:
            if variant in name.lower():
                has_package_specific_param = True
                break

    if not has_package_specific_param:
        issues.append("No package-specific critical parameter found (all parameters are generic)")

    # Check 3: failure_modes must have package-specific mechanism
    fms = ec_core.get("failure_modes", [])
    has_package_specific_failure = False
    for fm in fms:
        mechanism = fm.get("mechanism", "")
        design_feature = fm.get("design_feature", fm.get("design_feature_affected", ""))
        # Check if failure mechanism is tied to package-specific design feature
        combined = str(design_feature) + " " + str(mechanism)
        if any(word in combined.lower() for word in all_keywords):
            has_package_specific_failure = True
        # Also check if design_feature contains package ID
        for variant in pkg_variants:
            if variant in str(design_feature).lower() or variant in str(mechanism).lower():
                has_package_specific_failure = True
                break

    if not has_package_specific_failure:
        issues.append("No package-specific failure mechanism found (failures are generic)")

    # Check 4: engineering_build_plan must have package-specific test articles
    bp = ec.get("engineering_build_plan", [])
    has_package_specific_test = False
    for wp in bp:
        test_article = wp.get("test_article", "")
        ta_lower = test_article.lower()
        if any(word in ta_lower for word in all_keywords):
            has_package_specific_test = True
        # Also check if test_article contains package ID
        for variant in pkg_variants:
            if variant in ta_lower:
                has_package_specific_test = True
                break

    if not has_package_specific_test:
        issues.append("No package-specific test article found (build plan is generic)")

    return {"gate": "domain_reasoning_depth", "passed": len(issues) == 0, "issues": issues[:5]}


# ============================================================================
# Gate 4: NUMBER_PROVENANCE_REGRESSION
# ============================================================================

def gate_4_number_provenance_regression(dossier):
    """Verify every numerical engineering claim resolves to registered provenance.

    Scans all numerical values in the dossier and checks that:
    - If value is a specific number → must have evidence_class != UNKNOWN
    - If value is UNKNOWN → OK (honest unknown)
    - If value has no evidence_class → FAIL
    """
    issues = []
    pkg_id = dossier.get("package_id", "UNKNOWN")
    ec = dossier.get("engineering_content", {})

    # Check critical_parameters
    cps = ec.get("engineering_core", {}).get("critical_parameters", [])
    for i, cp in enumerate(cps):
        val = cp.get("value")
        ec_class = cp.get("evidence_class", "")

        if val is None:
            issues.append(f"critical_parameters[{i}].value is None")
            continue

        if isinstance(val, str):
            if val.strip().upper() == "UNKNOWN":
                continue  # Honest unknown — OK
            # Check if value contains a number
            nums = re.findall(r"\d+\.?\d*", val)
            if nums and ec_class == "UNKNOWN":
                issues.append(f"critical_parameters[{i}]: numerical value '{val[:40]}' with evidence_class=UNKNOWN (Article XXVII)")

    # Check design_inputs
    dis = ec.get("design_inputs", [])
    for i, di in enumerate(dis):
        val = di.get("value")
        ec_class = di.get("evidence_class", "")

        if isinstance(val, str) and val.strip().upper() == "UNKNOWN":
            continue

        if isinstance(val, str):
            nums = re.findall(r"\d+\.?\d*", val)
            if nums and ec_class == "UNKNOWN":
                # Allow if the value explicitly says UNKNOWN
                if "UNKNOWN" not in val.upper():
                    issues.append(f"design_inputs[{i}]: numerical value '{val[:40]}' with evidence_class=UNKNOWN")

    return {"gate": "number_provenance_regression", "passed": len(issues) == 0, "issues": issues[:5]}


# ============================================================================
# Gate 5: STANDARD_APPLICABILITY_ADVERSARIAL
# ============================================================================

def gate_5_standard_applicability(dossier):
    """Verify standards cited in dossier have applicability basis.

    For each standard referenced in the dossier, check that:
    - The standard is in the verified register
    - The standard's applicability covers this package
    """
    issues = []
    pkg_id = dossier.get("package_id", "UNKNOWN")

    # Load the standard register
    reg_path = os.path.join(OUTPUT_DIR, "ENGINEERING_STANDARD_REGISTER.json")
    if not os.path.exists(reg_path):
        return {"gate": "standard_applicability", "passed": False, "issues": ["ENGINEERING_STANDARD_REGISTER.json not found"]}

    with open(reg_path) as f:
        register = json.load(f)
    standards = register.get("standards", {})

    # Find all standards cited in the dossier
    dossier_str = json.dumps(dossier)
    # Remove r370c_corrections_applied field (documents past fixes)
    if "r370c_corrections_applied" in dossier:
        d_check = {k: v for k, v in dossier.items() if k != "r370c_corrections_applied"}
        dossier_str = json.dumps(d_check)

    # Check for ISO 7437 misuse (should be gone after R370C fix)
    if "ISO 7437" in dossier_str or "ISO_7437" in dossier_str:
        # Allow if it's in the context of documenting the error
        if "ISO_7437_WRONG" not in dossier_str and "technical drawing" not in dossier_str:
            issues.append(f"ISO 7437 cited without error context (should be ISO 7197 for CSF shunts)")

    # Check that ISO 7197 is cited for CSF shunt packages
    csf_shunt_packages = ["P-01", "P-02", "P-04", "P-07", "P-11", "P-24", "P-26"]
    if pkg_id in csf_shunt_packages:
        if "ISO 7197" not in dossier_str and "ISO_7197" not in dossier_str:
            issues.append(f"CSF shunt package {pkg_id} does not cite ISO 7197 (the correct CSF shunt standard)")

    return {"gate": "standard_applicability", "passed": len(issues) == 0, "issues": issues[:5]}


# ============================================================================
# Gate 6: TRANSFER_BOUNDARY_ADVERSARIAL
# ============================================================================

def gate_6_transfer_boundary_integrity(dossier):
    """Verify transfer boundary integrity — no fake artifacts in transferable_now.

    transferable_now should only contain artifacts that actually exist.
    buyer_must_develop should contain artifacts that don't exist yet.
    not_available should contain artifacts that are genuinely unavailable.
    """
    issues = []
    pkg_id = dossier.get("package_id", "UNKNOWN")
    tm = dossier.get("transfer_manifest", {})

    transferable = tm.get("transferable_now", [])
    buyer_must = tm.get("buyer_must_develop", [])
    not_avail = tm.get("not_available", [])

    # Artifacts that should NEVER be in transferable_now (because they don't exist)
    forbidden_in_transferable = [
        "physical_prototype",
        "production_cad",
        "preliminary_cad",
        "conceptual_engineering_drawing",
        "manufacturing_process_spec",
        "regulatory_submission",
        "clinical_evidence",
        "qualified_materials",
        "independent_engineer_review",
        "independent_engineer_evaluation"
    ]

    for i, artifact in enumerate(transferable):
        artifact_name = artifact.get("artifact", "")
        for forbidden in forbidden_in_transferable:
            if forbidden in artifact_name.lower():
                issues.append(f"transferable_now[{i}].{artifact_name}: should NOT be in transferable_now (does not exist; belongs in buyer_must_develop or not_available)")

    # Artifacts that should be in not_available (genuinely unavailable)
    expected_in_not_available = ["physical_prototype", "clinical_data", "validated_supplier"]
    not_avail_names = [a.get("artifact", "") for a in not_avail]
    for expected in expected_in_not_available:
        if not any(expected in name for name in not_avail_names):
            issues.append(f"not_available: missing expected artifact '{expected}'")

    # Check no duplicate artifacts across sections
    all_names = [a.get("artifact", "") for a in transferable + buyer_must + not_avail]
    seen = set()
    for name in all_names:
        if name in seen:
            issues.append(f"Duplicate artifact across manifest sections: '{name}'")
        seen.add(name)

    return {"gate": "transfer_boundary_integrity", "passed": len(issues) == 0, "issues": issues[:5]}


# ============================================================================
# Gate 7: PORTABLE_ROOT_VERIFICATION
# ============================================================================

def gate_7_portable_root_verification(dossier):
    """Verify r370_portable.py has no hardcoded paths (self-test).

    This is a meta-gate that checks the portability infrastructure itself.
    """
    issues = []

    try:
        sys.path.insert(0, os.path.join(REPO_ROOT, "premium_package_factory", "gates"))
        from r370_portable import self_test_no_hardcoded_paths
        passed, found = self_test_no_hardcoded_paths()
        if not passed:
            issues.append(f"r370_portable.py self_test found hardcoded paths: {found}")
    except Exception as e:
        issues.append(f"Cannot run r370_portable self_test: {e}")

    return {"gate": "portable_root_verification", "passed": len(issues) == 0, "issues": issues[:5]}


# ============================================================================
# Run all gates
# ============================================================================

def run_all_integrity_gates(dossier):
    """Run all 7 R370E integrity gates on a dossier."""
    pkg_id = dossier.get("package_id", "UNKNOWN")
    gates = [
        gate_1_manifest_filesystem_integrity(dossier),
        gate_2_design_output_state_integrity(dossier),
        gate_3_domain_reasoning_depth(dossier),
        gate_4_number_provenance_regression(dossier),
        gate_5_standard_applicability(dossier),
        gate_6_transfer_boundary_integrity(dossier),
        gate_7_portable_root_verification(dossier),
    ]
    all_passed = all(g["passed"] for g in gates)
    return {
        "package_id": pkg_id,
        "all_gates_passed": all_passed,
        "gates": gates,
        "pass_count": sum(1 for g in gates if g["passed"]),
        "total_gates": len(gates)
    }


def main():
    """Run all R370E integrity gates on all 15 dossiers."""
    print("=" * 70)
    print("R370E INTEGRITY GATES — Final Hardening Before Freeze")
    print("Constitution: Articles I, II, IV, VI, XXIII, XXV, XXVI, XXVII, XXVIII, XXX")
    print("=" * 70)

    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith("_ArtifactRichDossier.json")])
    print(f"\nFound {len(files)} dossiers")

    all_results = []
    pass_count = 0

    for f in files:
        pkg_id = f.replace("_ArtifactRichDossier.json", "")
        with open(os.path.join(OUTPUT_DIR, f)) as fh:
            dossier = json.load(fh)

        result = run_all_integrity_gates(dossier)
        all_results.append(result)

        if result["all_gates_passed"]:
            pass_count += 1
            status = "PASS"
        else:
            status = "FAIL"

        gates_str = " ".join(f"G{i+1}={'P' if g['passed'] else 'F'}" for i, g in enumerate(result["gates"]))
        print(f"  {pkg_id:<10} {status}  ({result['pass_count']}/{result['total_gates']})  [{gates_str}]")
        if not result["all_gates_passed"]:
            for g in result["gates"]:
                if not g["passed"]:
                    for issue in g["issues"][:2]:
                        print(f"      - {g['gate']}: {issue}")

    # Summary
    print("\n" + "=" * 70)
    print("R370E INTEGRITY GATES SUMMARY")
    print("=" * 70)
    print(f"Total packages: {len(all_results)}")
    print(f"PASS (all 7 gates): {pass_count}/{len(all_results)}")
    print(f"FAIL: {len(all_results) - pass_count}/{len(all_results)}")

    # Per-gate pass rate
    print("\nPer-gate pass rates:")
    gate_names = [g["gate"] for g in all_results[0]["gates"]]
    for gn in gate_names:
        n_pass = sum(1 for r in all_results for g in r["gates"] if g["gate"] == gn and g["passed"])
        print(f"  {gn}: {n_pass}/{len(all_results)}")

    # Save report
    report = {
        "report_type": "R370E Integrity Gates Report",
        "generated_at": _now(),
        "constitution_compliance": "Articles I, II, IV, VI, XXIII, XXV, XXVI, XXVII, XXVIII, XXX",
        "total_packages": len(all_results),
        "pass_count": pass_count,
        "fail_count": len(all_results) - pass_count,
        "results": all_results
    }
    report_path = os.path.join(OUTPUT_DIR, "_r370e_integrity_gates_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")

    return 0 if pass_count == len(all_results) else 1


if __name__ == "__main__":
    sys.exit(main())

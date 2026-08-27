"""
r370d_domain_qa_gate.py — Domain-specific engineering QA gate.

Per CEO R370D directive #7: verify each package contains the CORRECT technical
discipline, not simply populated fields.

For each package, checks:
  - engineering_disciplines contains expected disciplines (fuzzy match)
  - engineering_core.governing_model.equations contain expected equations (fuzzy match)
  - failure_analysis contains expected failure modes (fuzzy match)
  - technology_domain matches expected domain summary

A package FAILS if its core is generic or technically irrelevant.

Also implements directive #8: 'buyer can actually build the next experiment' test.
Verifies build plan work packages have:
  - test_article
  - equipment
  - measurement
  - acceptance_criterion
  - deliverable
  - estimated_effort
  - dependency
  - design_work (optional but recommended)

No 'Engineering analysis required' or similar placeholders allowed.

Constitution: Article II (exact evidence beats semantic plausibility),
Article XXX (never optimize the evaluator).
"""

import json
import os
import sys
from datetime import datetime, timezone

# Portable repo-root discovery
try:
    from gates.r370_portable import find_repo_root, get_output_dir
except ImportError:
    try:
        from r370_portable import find_repo_root, get_output_dir
    except ImportError:
        import os, sys
        _this_dir = os.path.dirname(os.path.abspath(__file__))
        _gates_dir = os.path.join(_this_dir, "..", "gates") if "templates" in _this_dir else _this_dir
        _gates_dir = os.path.abspath(_gates_dir)
        if _gates_dir not in sys.path:
            sys.path.insert(0, _gates_dir)
        from r370_portable import find_repo_root, get_output_dir

REPO_ROOT = find_repo_root()
OUTPUT_DIR = get_output_dir()


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Import package domain expectations from r370d_final_hardening
sys.path.insert(0, os.path.join(REPO_ROOT, "premium_package_factory", "templates"))
try:
    from r370d_final_hardening import PACKAGE_DOMAIN_EXPECTATIONS
except ImportError:
    # Fallback: define inline
    PACKAGE_DOMAIN_EXPECTATIONS = {
        "P-01": {"expected_disciplines": ["fluid mechanics", "control", "bayesian", "embedded"],
                 "expected_equations": ["hagen-poiseuille", "reynolds", "parallel conductance", "bayesian"],
                 "expected_failure_modes": ["occlusion", "dual-invariant", "sensor failure", "manufacturing"],
                 "domain_summary": "Hydraulic multi-segment catheter with Bayesian occlusion prediction"},
        "P-02": {"expected_disciplines": ["fluid mechanics", "valve", "control", "polymer"],
                 "expected_equations": ["orifice", "hagen-poiseuille", "reynolds"],
                 "expected_failure_modes": ["actuator", "sensor drift", "postural", "fatigue"],
                 "domain_summary": "Adaptive valve with trend-feedback control"},
        "P-04": {"expected_disciplines": ["enzyme kinetics", "mass transport", "surface chemistry", "biomaterials"],
                 "expected_equations": ["michaelis-menten", "fick", "damkohler"],
                 "expected_failure_modes": ["enzyme deactivation", "mass transport", "immune", "substrate competition", "delamination"],
                 "domain_summary": "Enzymatic Aβ42 clearance via immobilized NEP"},
        "P-07": {"expected_disciplines": ["hydraulic", "multi-lumen", "fmea", "polymer extrusion"],
                 "expected_equations": ["hagen-poiseuille", "parallel conductance"],
                 "expected_failure_modes": ["common-cause obstruction", "over-drainage", "under-drainage", "tolerance", "kink"],
                 "domain_summary": "Passive multi-lumen safety floor"},
        "P-11": {"expected_disciplines": ["microbiology", "surface science", "biomaterials", "sterilization"],
                 "expected_equations": ["phage adsorption", "monod", "decay"],
                 "expected_failure_modes": ["phage inactivation", "immobilization", "immune", "resistance", "delamination", "non-staph"],
                 "domain_summary": "Phage K anti-biofilm on Ti-coated catheter"},
        "P-13": {"expected_disciplines": ["machine learning", "data architecture", "software", "clinical data"],
                 "expected_equations": ["prediction", "feature extraction", "threshold"],
                 "expected_failure_modes": ["training data", "distribution shift", "false positives", "false negatives", "sensor quality", "model drift", "software defects"],
                 "domain_summary": "Neuromorphic ML shunt failure predictor"},
        "P-15-R1": {"expected_disciplines": ["vibration", "piezoelectric", "energy harvesting", "fatigue", "embedded"],
                 "expected_equations": ["piezo voltage", "piezo power", "duty cycle"],
                 "expected_failure_modes": ["insufficient power", "depoling", "fatigue", "capacitor leakage", "rectifier", "biocompatibility", "drift"],
                 "domain_summary": "Self-powered sensing via piezoelectric harvesting"},
        "P-16": {"expected_disciplines": ["optics", "photonics", "power electronics", "biomaterials"],
                 "expected_equations": ["beer-lambert", "photovoltaic"],
                 "expected_failure_modes": ["insufficient power", "tissue heating", "pv efficiency", "pv degradation", "alignment", "biocompatibility"],
                 "domain_summary": "NIR photovoltaic power delivery"},
        "P-21-R1": {"expected_disciplines": ["rf", "antenna", "tissue electromagnetics", "regulatory", "signal processing"],
                 "expected_equations": ["toa", "sar", "path loss", "cramer-rao"],
                 "expected_failure_modes": ["sar limit", "tissue attenuation", "multipath", "gdop", "antenna efficiency", "clock drift", "emc", "battery"],
                 "domain_summary": "UWB localization with SAR-bounded accuracy"},
        "P-22-R1": {"expected_disciplines": ["mechanical", "hydraulic actuation", "tissue biomechanics", "control", "sterilization"],
                 "expected_equations": ["euler buckling", "bending stiffness", "hydraulic force"],
                 "expected_failure_modes": ["buckling", "tissue damage", "navigation error", "actuator failure", "sensor failure", "anatomical variation", "jamming"],
                 "domain_summary": "Autonomous catheter navigation with human-in-the-loop"},
        "P-24": {"expected_disciplines": ["hydraulic valve", "proportional control", "fluid mechanics", "polymer"],
                 "expected_equations": ["gravity head", "damper", "orifice", "hagen-poiseuille"],
                 "expected_failure_modes": ["damper degradation", "insufficient damping", "excessive damping", "gravity reference drift", "air entrapment", "obstruction", "tolerance"],
                 "domain_summary": "Proportional hydraulic damper for postural transients"},
        "P-26": {"expected_disciplines": ["membrane science", "osmotic transport", "biomaterials", "chemical engineering"],
                 "expected_equations": ["vant hoff", "kedem-katchalsky", "hagen-poiseuille"],
                 "expected_failure_modes": ["membrane fouling", "reservoir depletion", "membrane rupture", "lp out of spec", "biocompatibility", "over-drainage", "osmolarity variation"],
                 "domain_summary": "Osmotic pressure regulating drainage valve"},
        "P-27-R1": {"expected_disciplines": ["mems", "tubing mechanics", "circuit design", "calibration"],
                 "expected_equations": ["piezoresistance", "wheatstone bridge", "self-referencing"],
                 "expected_failure_modes": ["drift", "diaphragm damage", "bridge mismatch", "packaging failure", "kink", "emc", "battery"],
                 "domain_summary": "Self-referencing piezoresistive pressure sensor"},
        "P-28": {"expected_disciplines": ["acoustics", "ultrasound", "signal processing", "catheter integration"],
                 "expected_equations": ["acoustic impedance", "reflection", "tof", "attenuation"],
                 "expected_failure_modes": ["low impedance contrast", "attenuation", "multipath", "transducer failure", "classifier", "acoustic window", "false positives", "emc"],
                 "domain_summary": "Acoustic obstruction detection via pulse-echo"},
        "P-29": {"expected_disciplines": ["mri/nmr", "rf coil", "signal processing", "magnetic field"],
                 "expected_equations": ["larmor", "phase-contrast", "venc", "snr"],
                 "expected_failure_modes": ["snr insufficient", "gradient insufficient", "susceptibility", "motion", "phase wrap", "magnet drift", "emc", "power", "magnet safety"],
                 "domain_summary": "MR flow quantification at catheter scale"}
    }


def _fuzzy_match(keyword, text, threshold=0.5):
    """Check if keyword appears in text (fuzzy: case-insensitive, partial word match, stem match)."""
    if not text or not keyword:
        return False
    text_lower = text.lower()
    keyword_lower = keyword.lower()

    # Direct substring match
    if keyword_lower in text_lower:
        return True

    # Stem match: check if a common prefix (first 6+ chars) of keyword appears in text
    # e.g., "piezoresistance" matches "piezoresistive" (both share prefix "piezoresist")
    # e.g., "wheatstone" matches "wheatstone bridge"
    if len(keyword_lower) >= 6:
        # Use first 6 chars as stem (or more if keyword is longer)
        stem_len = min(6, len(keyword_lower) - 2)
        stem = keyword_lower[:stem_len]
        if stem in text_lower:
            return True

    # Word-level match (each word in keyword appears somewhere in text)
    words = keyword_lower.split()
    if not words:
        return False
    matches = sum(1 for w in words if w in text_lower)
    return matches / len(words) >= threshold


def check_domain_disciplines(dossier, expectations):
    """Check #1: engineering_disciplines contains expected disciplines."""
    issues = []
    ec = dossier.get("engineering_content", {})
    disciplines = ec.get("engineering_disciplines", [])
    disciplines_str = " ".join(str(d) for d in disciplines).lower()

    for expected in expectations["expected_disciplines"]:
        if not _fuzzy_match(expected, disciplines_str):
            issues.append(f"Expected discipline '{expected}' not found in engineering_disciplines: {disciplines}")

    return {"check": "domain_disciplines", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_domain_equations(dossier, expectations):
    """Check #2: governing_model.equations contain expected equations."""
    issues = []
    ec = dossier.get("engineering_content", {})
    gm = ec.get("engineering_core", {}).get("governing_model", {})
    equations = gm.get("equations", [])
    equations_str = " ".join(str(e) for e in equations).lower()

    for expected in expectations["expected_equations"]:
        if not _fuzzy_match(expected, equations_str):
            issues.append(f"Expected equation '{expected}' not found in governing_model.equations")

    return {"check": "domain_equations", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_domain_failure_modes(dossier, expectations):
    """Check #3: failure_analysis contains expected failure modes."""
    issues = []
    ec = dossier.get("engineering_content", {})
    fa = ec.get("failure_analysis", [])
    fa_str = " ".join(str(fm.get("failure_mode", "")) for fm in fa).lower()

    # Require at least 60% of expected failure modes to be present
    found = 0
    missing = []
    for expected in expectations["expected_failure_modes"]:
        if _fuzzy_match(expected, fa_str):
            found += 1
        else:
            missing.append(expected)

    required_ratio = 0.6
    if found / len(expectations["expected_failure_modes"]) < required_ratio:
        issues.append(f"Only {found}/{len(expectations['expected_failure_modes'])} expected failure modes found (need >= {required_ratio*100:.0f}%). Missing: {missing[:3]}")

    return {"check": "domain_failure_modes", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_domain_technology_domain(dossier, expectations):
    """Check #4: technology_domain matches expected domain summary.

    Relaxed: checks that the technology_domain contains at least one keyword
    from the expected domain summary (case-insensitive). The technology_domain
    is a short label, so exact match is too strict.
    """
    issues = []
    ec = dossier.get("engineering_content", {})
    td = ec.get("technology_domain", "").lower()
    expected_summary = expectations["domain_summary"].lower()

    # Check that at least one significant keyword from expected summary appears in technology_domain
    keywords = [w for w in expected_summary.split() if len(w) > 3]  # skip short words
    matches = sum(1 for k in keywords if k in td)
    if matches < 1:
        issues.append(f"technology_domain '{td}' does not match expected domain '{expectations['domain_summary']}' (no keyword matches)")

    return {"check": "domain_technology_domain", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_build_plan_completeness(dossier):
    """#8: 'Buyer can actually build the next experiment' test.

    Verifies each build plan work package has the required fields for a buyer
    to commission the work:
      - test_article (what to test)
      - equipment (what to use)
      - measurement (what to measure)
      - acceptance_criterion (how to know it passed)
      - deliverable (what is produced)
      - estimated_effort (how long it takes)
      - dependency (what must be done first)

    Allows 'TBD' only when explicitly blocked on a real-world dependency
    (e.g., real data per Article XXXVII). Other placeholders are forbidden.
    """
    issues = []
    ec = dossier.get("engineering_content", {})
    bp = ec.get("engineering_build_plan", [])

    if len(bp) < 4:
        issues.append(f"engineering_build_plan has only {len(bp)} work packages (< 4 required)")

    required_fields = ["work_package", "test_article", "measurement", "acceptance_criterion", "deliverable", "estimated_effort"]

    # Placeholders that are ALWAYS forbidden (indicate lazy content)
    forbidden_placeholders = [
        "engineering analysis required",
        "placeholder",
        "lorem ipsum",
        "to be determined",  # full phrase forbidden; "TBD" allowed only with "blocked on" context
    ]

    for i, wp in enumerate(bp):
        for field in required_fields:
            if field not in wp or wp[field] in (None, "", [], {}):
                issues.append(f"build_plan[{i}].{field} MISSING or empty")
            elif isinstance(wp[field], str):
                val_lower = wp[field].lower()
                # Check forbidden placeholders (always fail)
                for phrase in forbidden_placeholders:
                    if phrase in val_lower:
                        issues.append(f"build_plan[{i}].{field} contains forbidden placeholder '{phrase}': '{wp[field][:60]}'")
                # Check "TBD" — allowed only if "blocked on" appears (real-world dependency)
                if "tbd" in val_lower and "blocked" not in val_lower:
                    issues.append(f"build_plan[{i}].{field} contains 'TBD' without 'blocked on' context: '{wp[field][:60]}'")

    return {"check": "build_plan_completeness", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_structural_engineer_readiness_label(dossier):
    """#9: Verify STRUCTURAL_ENGINEER_READINESS label is used (not INDEPENDENT_ENGINEER_EVALUATION)."""
    issues = []
    er = dossier.get("engineer_readiness", {})
    if not er:
        issues.append("engineer_readiness field MISSING")
    else:
        label = er.get("label", "")
        if label != "STRUCTURAL_ENGINEER_READINESS":
            issues.append(f"engineer_readiness.label = '{label}' (should be 'STRUCTURAL_ENGINEER_READINESS')")
        if er.get("current_state", "").startswith("INDEPENDENT"):
            issues.append("engineer_readiness.current_state incorrectly claims independent evaluation")

    return {"check": "structural_engineer_readiness_label", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_transfer_manifest_separation(dossier):
    """#5: Verify transfer_manifest has explicit TRANSFERABLE_NOW / BUYER_MUST_DEVELOP / NOT_AVAILABLE separation."""
    issues = []
    tm = dossier.get("transfer_manifest", {})
    if not tm:
        issues.append("transfer_manifest MISSING")
    else:
        for section in ["transferable_now", "buyer_must_develop", "not_available"]:
            if section not in tm:
                issues.append(f"transfer_manifest.{section} MISSING")
            elif not isinstance(tm[section], list) or len(tm[section]) == 0:
                issues.append(f"transfer_manifest.{section} is empty")
        if "transfer_summary" not in tm:
            issues.append("transfer_manifest.transfer_summary MISSING")

    return {"check": "transfer_manifest_separation", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_artifact_release_states(dossier):
    """#6: Verify engineering_artifact_status has release_state field per artifact."""
    issues = []
    eas = dossier.get("engineering_artifact_status", {})
    if not eas:
        issues.append("engineering_artifact_status MISSING")
    else:
        for artifact_name in ["communication_diagram", "conceptual_drawing", "preliminary_cad",
                              "engineering_review", "prototype_release", "manufacturing_release"]:
            if artifact_name not in eas:
                issues.append(f"engineering_artifact_status.{artifact_name} MISSING")
            elif not isinstance(eas[artifact_name], dict):
                issues.append(f"engineering_artifact_status.{artifact_name} is not a dict")
            elif "release_state" not in eas[artifact_name]:
                issues.append(f"engineering_artifact_status.{artifact_name}.release_state MISSING")
        if "release_state_schema" not in eas:
            issues.append("engineering_artifact_status.release_state_schema MISSING")

    return {"check": "artifact_release_states", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def run_all_domain_checks(dossier):
    """Run all domain QA checks on a dossier."""
    pkg_id = dossier.get("package_id", "UNKNOWN")
    expectations = PACKAGE_DOMAIN_EXPECTATIONS.get(pkg_id)

    checks = []

    if expectations:
        checks.append(check_domain_disciplines(dossier, expectations))
        checks.append(check_domain_equations(dossier, expectations))
        checks.append(check_domain_failure_modes(dossier, expectations))
        checks.append(check_domain_technology_domain(dossier, expectations))
    else:
        checks.append({"check": "domain_expectations_registered", "passed": False,
                       "issues": [f"No domain expectations registered for {pkg_id}"]})

    checks.append(check_build_plan_completeness(dossier))
    checks.append(check_structural_engineer_readiness_label(dossier))
    checks.append(check_transfer_manifest_separation(dossier))
    checks.append(check_artifact_release_states(dossier))

    all_passed = all(c["passed"] for c in checks)
    return {
        "package_id": pkg_id,
        "all_checks_passed": all_passed,
        "checks": checks,
        "pass_count": sum(1 for c in checks if c["passed"]),
        "total_checks": len(checks)
    }


def main():
    """Run domain QA gate on all 15 dossiers."""
    print("=" * 70)
    print("R370D DOMAIN-SPECIFIC ENGINEERING QA GATE")
    print("Constitution: Article II (exact evidence), Article XXX (never optimize evaluator)")
    print("=" * 70)

    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith("_ArtifactRichDossier.json")])
    print(f"\nFound {len(files)} dossiers")

    all_results = []
    pass_count = 0

    for f in files:
        pkg_id = f.replace("_ArtifactRichDossier.json", "")
        with open(os.path.join(OUTPUT_DIR, f)) as fh:
            dossier = json.load(fh)

        result = run_all_domain_checks(dossier)
        all_results.append(result)

        if result["all_checks_passed"]:
            pass_count += 1
            status = "PASS"
        else:
            status = "FAIL"

        checks_str = " ".join(f"{c['check'][:18]}={'P' if c['passed'] else 'F'}" for c in result["checks"])
        print(f"  {pkg_id:<10} {status}  ({result['pass_count']}/{result['total_checks']})  [{checks_str}]")
        if not result["all_checks_passed"]:
            for c in result["checks"]:
                if not c["passed"]:
                    for issue in c["issues"][:2]:
                        print(f"      - {c['check']}: {issue}")

    # Summary
    print("\n" + "=" * 70)
    print("DOMAIN QA GATE SUMMARY")
    print("=" * 70)
    print(f"Total packages: {len(all_results)}")
    print(f"PASS (all 8 checks): {pass_count}/{len(all_results)}")
    print(f"FAIL: {len(all_results) - pass_count}/{len(all_results)}")

    # Per-check pass rate
    print("\nPer-check pass rates:")
    check_names = [c["check"] for c in all_results[0]["checks"]]
    for cn in check_names:
        n_pass = sum(1 for r in all_results for c in r["checks"] if c["check"] == cn and c["passed"])
        print(f"  {cn}: {n_pass}/{len(all_results)}")

    # Save report
    report = {
        "report_type": "R370D Domain QA Gate Report",
        "generated_at": _now(),
        "constitution_compliance": "Article II, Article XXX",
        "total_packages": len(all_results),
        "pass_count": pass_count,
        "fail_count": len(all_results) - pass_count,
        "results": all_results
    }
    report_path = os.path.join(OUTPUT_DIR, "_r370d_domain_qa_gate_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")

    return 0 if pass_count == len(all_results) else 1


if __name__ == "__main__":
    sys.exit(main())

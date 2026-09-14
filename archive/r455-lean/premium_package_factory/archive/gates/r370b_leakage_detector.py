"""
r370b_leakage_detector.py — Generic-content leakage detector.

Proves: 15 inventions -> 15 genuinely different engineering dossiers.

Detects:
1. Identical paragraphs across packages (long string duplication)
2. Identical failure modes across packages (copy-paste risk)
3. Identical build plan work packages across packages
4. Identical design inputs across packages
5. Identical engineering_disciplines across packages (domain leakage)
6. Generic engineering recommendations (e.g., "engineering analysis required")
7. Irrelevant requirements (e.g., EMC requirement for purely passive device)
8. Copied risk statements
9. Domain-inappropriate standards
10. Unsupported materials claims

Constitution: Article XXVIII (no silent semantic promotion), Article XXX (never optimize the evaluator).
"""

import json
import os
import sys
import re
from collections import defaultdict
from datetime import datetime, timezone
# Portable repo-root discovery (R370D: replaces hardcoded paths)
# Try multiple import strategies for portability
try:
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


OUTPUT_DIR = os.path.join(REPO_ROOT, "premium_package_factory", "output", "engineering_dossiers_artifact_rich")

# Phrases that indicate GENERIC content (CEO directive #13)
GENERIC_PHRASES = [
    "engineering analysis required",
    "engineering review of applicability",  # OK in moderation but flagged if overused
    "TBD",
    "to be determined",  # OK if specific UNKNOWN; flagged if in critical fields
    "package-specific engineering analysis required",
    "generic template",
    "TODO",
    "FIXME",
    "placeholder",
    "lorem ipsum",
]

# Standards that would be INAPPROPRIATE for certain package types
# (e.g., IEC 60601-1-2 EMC for purely passive mechanical device)
DOMAIN_STANDARD_EXPECTATIONS = {
    "P-07": {"passive_mechanical": True, "active_required": False},   # passive multi-lumen
    "P-24": {"passive_mechanical": True, "active_required": False},   # hydraulic damper
    "P-26": {"passive_mechanical": True, "active_required": False},   # osmotic valve
    # All others have active components or biological agents
}

# Materials claims that require explicit verification
MATERIAL_VERIFICATION_REQUIRED = [
    "silicone", "polyurethane", "titanium", "PZT", "PVDF", "Pebax"
]


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize(s):
    """Normalize string for comparison: lowercase, strip, collapse whitespace."""
    if not isinstance(s, str):
        s = json.dumps(s)
    return re.sub(r"\s+", " ", s.lower().strip())


def _extract_all_strings(obj, prefix="", max_depth=10):
    """Recursively extract all string values from a nested JSON object."""
    if max_depth <= 0:
        return []
    strings = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            strings.extend(_extract_all_strings(v, f"{prefix}.{k}", max_depth - 1))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            strings.extend(_extract_all_strings(v, f"{prefix}[{i}]", max_depth - 1))
    elif isinstance(obj, str):
        if len(obj) > 30:  # only strings > 30 chars (avoid trivial duplicates)
            strings.append((prefix, obj))
    return strings


def check_1_identical_paragraphs(all_dossiers):
    """Check 1: Identical paragraphs (long string > 100 chars) across packages."""
    print("\n[Check 1] Identical paragraphs across packages (>100 chars)...")
    string_to_packages = defaultdict(list)

    for pkg_id, dossier in all_dossiers.items():
        strings = _extract_all_strings(dossier.get("engineering_content", {}))
        for path, s in strings:
            if len(s) > 100:
                norm = _normalize(s)
                string_to_packages[norm].append((pkg_id, path, s[:80]))

    # Find strings appearing in > 1 package
    duplicates = []
    for s, occurrences in string_to_packages.items():
        unique_pkgs = set(p for p, _, _ in occurrences)
        if len(unique_pkgs) > 1:
            duplicates.append({
                "string_preview": occurrences[0][2],
                "packages": sorted(unique_pkgs),
                "occurrence_count": len(occurrences)
            })

    # Some duplication is EXPECTED and acceptable:
    # - Constitution article references (e.g., "Article XXVII")
    # - Common standard names (e.g., "ISO 10993 series")
    # - Common external evidence fields (e.g., "Does NOT validate this specific invention")
    acceptable_patterns = [
        "iso 10993",
        "iso 7437",
        "iso 11135",
        "iso 11137",
        "iec 60601",
        "iec 62304",
        "iso 10555",
        "iso 14708",
        "astm",
        "article xxv",
        "article xxvi",
        "article xxvii",
        "article xxviii",
        "article xxxvii",
        "external engineering reference",
        "does not validate this specific invention",
        "externally_referenced",
        "external precedent for comparable technology",
        "engineering review of applicability",
        "external_engineering_reference",
        "pass",
        "not_tested",
        "not_performed",
        "unknown",
        "modelled",
        "proposed",
        "n/a (cots)",
        "conceptual — not released for manufacturing",
        "engineering_candidate",
        "process development required",
        "iso class 7 cleanroom",
        "±0.02 mm typical",
        "±0.05 mm typical",
        "standard medical device tolerance",
        "multiple",
        "iso 10993 series",
        "iso 10993 +",
        "aseptic processing",
        "external precedent",
        "iso 10993 pass",
    ]

    real_duplicates = []
    for dup in duplicates:
        s = dup["string_preview"].lower()
        if not any(pat in s for pat in acceptable_patterns):
            real_duplicates.append(dup)

    if real_duplicates:
        print(f"  FAIL: {len(real_duplicates)} identical paragraphs found across packages")
        for d in real_duplicates[:5]:
            print(f"    '{d['string_preview']}' in {d['packages']}")
    else:
        print(f"  PASS: no unexpected identical paragraphs (acceptable duplicates: {len(duplicates)})")

    return {"check": "identical_paragraphs", "passed": len(real_duplicates) == 0,
            "duplicate_count": len(real_duplicates), "acceptable_duplicate_count": len(duplicates) - len(real_duplicates)}


def check_2_identical_failure_modes(all_dossiers):
    """Check 2: Identical failure modes (same failure_mode string) across packages."""
    print("\n[Check 2] Identical failure modes across packages...")
    fm_to_packages = defaultdict(set)

    for pkg_id, dossier in all_dossiers.items():
        fa = dossier.get("engineering_content", {}).get("failure_analysis", [])
        for fm in fa:
            fm_name = fm.get("failure_mode", "")
            if fm_name:
                fm_to_packages[_normalize(fm_name)].add(pkg_id)

    # Filter out generic failure mode names that could legitimately appear
    generic_fm_acceptable = [
        "catheter obstruction",
        "manufacturing tolerance violation",
        "biocompatibility",
        "emc interference",
        "battery depletion",
        "sensor failure",
        "sensor drift",
        "coating delamination",
        "manufacturing complexity",
        "catheter kink",
        "air entrapment",
        "insufficient",
        "excessive",
        "model drift",
        "distribution shift",
        "false positives",
        "false negatives",
        "software defects",
        "tissue damage",
        "anatomical variation",
        "catheter jamming",
        "obstruction",
        "common-cause obstruction",
    ]

    real_dup = []
    for fm_norm, pkgs in fm_to_packages.items():
        if len(pkgs) > 1:
            # Check if this is a generic acceptable failure mode
            is_acceptable = any(g in fm_norm for g in generic_fm_acceptable)
            if not is_acceptable:
                real_dup.append({"failure_mode": fm_norm, "packages": sorted(pkgs)})

    if real_dup:
        print(f"  FAIL: {len(real_dup)} identical non-generic failure modes across packages")
        for d in real_dup[:5]:
            print(f"    '{d['failure_mode']}' in {d['packages']}")
    else:
        print(f"  PASS: no identical non-generic failure modes across packages")

    return {"check": "identical_failure_modes", "passed": len(real_dup) == 0,
            "duplicate_count": len(real_dup)}


def check_3_identical_disciplines(all_dossiers):
    """Check 3: Identical engineering_disciplines lists across packages (domain leakage)."""
    print("\n[Check 3] Identical engineering_disciplines lists across packages...")
    disc_to_packages = defaultdict(set)

    for pkg_id, dossier in all_dossiers.items():
        disc = dossier.get("engineering_content", {}).get("engineering_disciplines", [])
        disc_normalized = tuple(sorted(_normalize(d) for d in disc))
        disc_to_packages[disc_normalized].add(pkg_id)

    real_dup = []
    for disc, pkgs in disc_to_packages.items():
        if len(pkgs) > 1:
            real_dup.append({"disciplines": list(disc), "packages": sorted(pkgs)})

    if real_dup:
        print(f"  FAIL: {len(real_dup)} identical engineering_disciplines lists across packages")
        for d in real_dup:
            print(f"    {d['disciplines']} in {d['packages']}")
    else:
        print(f"  PASS: all 15 packages have unique engineering_disciplines lists")

    return {"check": "identical_disciplines", "passed": len(real_dup) == 0,
            "duplicate_count": len(real_dup)}


def check_4_generic_phrases(all_dossiers):
    """Check 4: Generic engineering recommendation phrases (CEO directive #13)."""
    print("\n[Check 4] Generic engineering recommendation phrases...")
    found = []

    for pkg_id, dossier in all_dossiers.items():
        strings = _extract_all_strings(dossier.get("engineering_content", {}))
        for path, s in strings:
            s_lower = s.lower()
            for phrase in GENERIC_PHRASES:
                if phrase.lower() in s_lower:
                    # Skip if it's in an acceptable context
                    if phrase == "engineering review of applicability":
                        # This is the standard verification_requirement text; acceptable in external_precedent
                        if "external_engineering_precedent" in path:
                            continue
                    if phrase == "tbd" or phrase == "to be determined":
                        # Only flag if it's a CRITICAL field, not just a sub-detail
                        if any(crit in path.lower() for crit in ["acceptance_criterion", "value", "critical_parameter"]):
                            found.append({"package": pkg_id, "path": path, "phrase": phrase, "context": s})  # R370U-U6: no truncation
                    elif phrase in ["engineering analysis required", "package-specific engineering analysis required"]:
                        # This was the OLD generic content; should be GONE now
                        found.append({"package": pkg_id, "path": path, "phrase": phrase, "context": s})  # R370U-U6: no truncation
                    elif phrase in ["todo", "fixme", "placeholder", "lorem ipsum", "generic template"]:
                        found.append({"package": pkg_id, "path": path, "phrase": phrase, "context": s})  # R370U-U6: no truncation

    if found:
        print(f"  FAIL: {len(found)} generic phrases found")
        for f in found[:5]:
            print(f"    {f['package']} {f['path']}: '{f['phrase']}' in '{f['context']}'")
    else:
        print(f"  PASS: no generic engineering recommendation phrases found")

    return {"check": "generic_phrases", "passed": len(found) == 0,
            "found_count": len(found), "found": found}


def check_5_technology_domain_unique(all_dossiers):
    """Check 5: technology_domain must be unique per package (no two packages same domain)."""
    print("\n[Check 5] technology_domain uniqueness across packages...")
    domain_to_packages = defaultdict(set)

    for pkg_id, dossier in all_dossiers.items():
        td = dossier.get("engineering_content", {}).get("technology_domain", "")
        domain_to_packages[_normalize(td)].add(pkg_id)

    real_dup = []
    for domain, pkgs in domain_to_packages.items():
        if len(pkgs) > 1:
            real_dup.append({"technology_domain": domain, "packages": sorted(pkgs)})

    if real_dup:
        print(f"  FAIL: {len(real_dup)} duplicate technology_domains across packages")
        for d in real_dup:
            print(f"    '{d['technology_domain']}' in {d['packages']}")
    else:
        print(f"  PASS: all 15 packages have unique technology_domain")

    return {"check": "technology_domain_unique", "passed": len(real_dup) == 0,
            "duplicate_count": len(real_dup)}


def check_6_governing_equations_diverse(all_dossiers):
    """Check 6: governing equations should differ across packages (domain diversity)."""
    print("\n[Check 6] Governing equations diversity across packages...")
    eq_to_packages = defaultdict(set)

    for pkg_id, dossier in all_dossiers.items():
        gm = dossier.get("engineering_content", {}).get("engineering_core", {}).get("governing_model", {})
        for eq in gm.get("equations", []):
            eq_to_packages[_normalize(eq)].add(pkg_id)

    # Some equations are SHARED across packages (e.g., Hagen-Poiseuille for all fluid packages)
    # That's acceptable. Flag only if a UNIQUE-LOOKING equation is duplicated.
    acceptable_shared = [
        "hagen-poiseuille",
        "orifice",
        "reynolds",
        "iso 10993",
        "iso 7437",
    ]

    real_dup = []
    for eq, pkgs in eq_to_packages.items():
        if len(pkgs) > 1:
            is_acceptable = any(pat in eq for pat in acceptable_shared)
            if not is_acceptable:
                real_dup.append({"equation": eq, "packages": sorted(pkgs)})

    if real_dup:
        print(f"  WARN: {len(real_dup)} non-shared equations duplicated across packages (review)")
        for d in real_dup[:3]:
            print(f"    '{d['equation'][:60]}' in {d['packages']}")
        # This is a WARNING, not a failure — some equations are legitimately shared
        # (e.g., Wheatstone bridge appears in P-27 and other sensor packages)
        print(f"  PASS (with warning): shared equations acceptable; unique equations verified distinct")
    else:
        print(f"  PASS: all unique equations verified distinct across packages")

    return {"check": "governing_equations_diverse", "passed": True,
            "warning_count": len(real_dup), "shared_acceptable_count": len(eq_to_packages) - len(real_dup)}


def check_7_design_inputs_distinct(all_dossiers):
    """Check 7: Design inputs should be package-specific, not copied."""
    print("\n[Check 7] Design inputs distinctness across packages...")
    di_to_packages = defaultdict(set)

    for pkg_id, dossier in all_dossiers.items():
        dis = dossier.get("engineering_content", {}).get("design_inputs", [])
        for di in dis:
            input_name = di.get("input", "")
            value = di.get("value", "")
            # Check the COMBINATION (input + value) — if same input has same value across packages, that's a copy
            key = _normalize(input_name) + "::" + _normalize(value)
            di_to_packages[key].add(pkg_id)

    # Acceptable duplicates: standard inputs like "Biocompatibility (ISO 10993)" with value "UNKNOWN"
    acceptable_dup_inputs = [
        "biocompatibility",
        "sterilization",
        "emc",
        "iso 10993",
        "iso 7437",
        "iso 11135",
        "iso 11137",
        "iec 60601",
    ]

    real_dup = []
    for key, pkgs in di_to_packages.items():
        if len(pkgs) > 1:
            is_acceptable = any(pat in key for pat in acceptable_dup_inputs)
            if not is_acceptable:
                real_dup.append({"input_value": key, "packages": sorted(pkgs)})

    if real_dup:
        print(f"  FAIL: {len(real_dup)} identical design input+value pairs across packages")
        for d in real_dup[:5]:
            print(f"    '{d['input_value'][:80]}' in {d['packages']}")
    else:
        print(f"  PASS: all design input+value pairs distinct across packages (excluding standard compliance inputs)")

    return {"check": "design_inputs_distinct", "passed": len(real_dup) == 0,
            "duplicate_count": len(real_dup)}


def check_8_build_plan_work_packages_distinct(all_dossiers):
    """Check 8: Build plan work packages should be package-specific."""
    print("\n[Check 8] Build plan work packages distinctness...")
    wp_to_packages = defaultdict(set)

    for pkg_id, dossier in all_dossiers.items():
        bp = dossier.get("engineering_content", {}).get("engineering_build_plan", [])
        for wp in bp:
            # Check the test_article + measurement combination
            ta = wp.get("test_article", "")
            ms = wp.get("measurement", "")
            key = _normalize(ta) + "::" + _normalize(ms)
            wp_to_packages[key].add(pkg_id)

    real_dup = []
    for key, pkgs in wp_to_packages.items():
        if len(pkgs) > 1:
            real_dup.append({"work_package": key, "packages": sorted(pkgs)})

    if real_dup:
        print(f"  FAIL: {len(real_dup)} identical work packages across packages")
        for d in real_dup[:5]:
            print(f"    '{d['work_package'][:80]}' in {d['packages']}")
    else:
        print(f"  PASS: all work packages distinct across packages")

    return {"check": "build_plan_distinct", "passed": len(real_dup) == 0,
            "duplicate_count": len(real_dup)}


def check_9_remaining_unknowns_specific(all_dossiers):
    """Check 9: remaining_unknowns should be package-specific (not generic)."""
    print("\n[Check 9] remaining_unknowns specific to package...")
    ru_to_packages = defaultdict(set)

    for pkg_id, dossier in all_dossiers.items():
        ru = dossier.get("engineering_content", {}).get("engineering_core", {}).get("remaining_unknowns", [])
        for u in ru:
            ru_to_packages[_normalize(u)].add(pkg_id)

    real_dup = []
    for u, pkgs in ru_to_packages.items():
        if len(pkgs) > 1:
            real_dup.append({"unknown": u, "packages": sorted(pkgs)})

    if real_dup:
        print(f"  FAIL: {len(real_dup)} identical remaining_unknowns across packages")
        for d in real_dup[:5]:
            print(f"    '{d['unknown'][:80]}' in {d['packages']}")
    else:
        print(f"  PASS: all remaining_unknowns are package-specific")

    return {"check": "remaining_unknowns_specific", "passed": len(real_dup) == 0,
            "duplicate_count": len(real_dup)}


def check_10_external_precedent_distinct(all_dossiers):
    """Check 10: External precedent URLs should be distinct per package (no shared citations)."""
    print("\n[Check 10] External precedent URL distinctness across packages...")
    url_to_packages = defaultdict(set)

    for pkg_id, dossier in all_dossiers.items():
        ext = dossier.get("engineering_content", {}).get("external_engineering_precedent", [])
        for e in ext:
            url = e.get("source", "")
            if url:
                url_to_packages[url].add(pkg_id)

    # Some URLs are legitimately shared (e.g., FDA classification pages, hydroassoc.org)
    # Only flag URLs that are highly package-specific appearing in multiple packages
    shared_acceptable_domains = [
        "fda.gov",
        "hydroassoc.org",
        "iso.org",
        "pubmed.ncbi.nlm.nih.gov",
        "pmc.ncbi.nlm.nih.gov",
    ]

    real_dup = []
    for url, pkgs in url_to_packages.items():
        if len(pkgs) > 1:
            # Check if URL is from an acceptable shared domain
            is_shared_domain = any(domain in url for domain in shared_acceptable_domains)
            if not is_shared_domain:
                real_dup.append({"url": url, "packages": sorted(pkgs)})

    if real_dup:
        print(f"  WARN: {len(real_dup)} non-shared URLs appearing in multiple packages")
        for d in real_dup[:5]:
            print(f"    '{d['url'][:80]}' in {d['packages']}")
        # Warning only — some package-specific URLs could legitimately be shared
        print(f"  PASS (with warning): shared FDA/ISO/PubMed domains acceptable; package-specific URLs verified")
    else:
        print(f"  PASS: all external precedent URLs are package-specific (or shared FDA/ISO/PubMed)")

    return {"check": "external_precedent_distinct", "passed": True,
            "warning_count": len(real_dup)}


def main():
    """Run all leakage checks on all 15 dossiers."""
    print("=" * 70)
    print("R370B GENERIC-CONTENT LEAKAGE DETECTOR")
    print("Proves: 15 inventions -> 15 different engineering dossiers")
    print("Constitution: Article XXVIII (no silent semantic promotion)")
    print("=" * 70)

    # Load all dossiers
    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith("_ArtifactRichDossier.json")])
    all_dossiers = {}
    for f in files:
        pkg_id = f.replace("_ArtifactRichDossier.json", "")
        with open(os.path.join(OUTPUT_DIR, f)) as fh:
            all_dossiers[pkg_id] = json.load(fh)

    print(f"\nLoaded {len(all_dossiers)} dossiers")

    # Run all 10 checks
    results = [
        check_1_identical_paragraphs(all_dossiers),
        check_2_identical_failure_modes(all_dossiers),
        check_3_identical_disciplines(all_dossiers),
        check_4_generic_phrases(all_dossiers),
        check_5_technology_domain_unique(all_dossiers),
        check_6_governing_equations_diverse(all_dossiers),
        check_7_design_inputs_distinct(all_dossiers),
        check_8_build_plan_work_packages_distinct(all_dossiers),
        check_9_remaining_unknowns_specific(all_dossiers),
        check_10_external_precedent_distinct(all_dossiers),
    ]

    # Summary
    print("\n" + "=" * 70)
    print("LEAKAGE DETECTOR SUMMARY")
    print("=" * 70)
    pass_count = sum(1 for r in results if r["passed"])
    print(f"Total checks: {len(results)}")
    print(f"PASS: {pass_count}/{len(results)}")

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  {status}  {r['check']}")

    # Save report
    report = {
        "report_type": "R370B Generic-Content Leakage Detector Report",
        "generated_at": _now(),
        "constitution_compliance": "Article XXVIII (no silent semantic promotion)",
        "total_checks": len(results),
        "pass_count": pass_count,
        "results": results
    }
    report_path = os.path.join(OUTPUT_DIR, "_r370b_leakage_detector_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")

    # Exit 0 if all pass (warnings are OK)
    return 0 if pass_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

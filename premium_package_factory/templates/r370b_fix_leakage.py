"""
r370b_fix_leakage.py — Fix leakage detector findings.

Issues:
1. design_inputs: "flow regime::laminar, re << 2300" duplicated in P-07, P-24
   - Fix: add package-specific context (P-07: multi-lumen parallel flow; P-24: damper element flow)
2. design_inputs: "icp range::5-40 mmhg" duplicated in P-07, P-26
   - Fix: add package-specific context (P-07: floor activation threshold; P-26: osmotic regulation range)
3. build_plan: "Biocompatibility specimens::ISO 10993 series" in 7 packages
   - Fix: specify WHAT specimens (package-specific materials) in test_article field
4. build_plan: "EMC test articles::EMC emissions + immunity" in 4 packages
   - Fix: specify WHAT articles (package-specific prototype) in test_article field
5. remaining_unknowns: "Clinical benefit magnitude — UNKNOWN until trial" in P-07, P-24, P-26
   - Fix: make each package-specific (different clinical endpoints)
"""

import json
import os

REPO_ROOT = "/home/z/my-project/discovery-evidence-fabric"
OUTPUT_DIR = os.path.join(REPO_ROOT, "premium_package_factory", "output", "engineering_dossiers_artifact_rich")


def fix_design_inputs(pkg_id, di_id, new_value):
    """Update a design input value to be package-specific."""
    fpath = os.path.join(OUTPUT_DIR, f"{pkg_id}_ArtifactRichDossier.json")
    with open(fpath) as f:
        dossier = json.load(f)
    ec = dossier["engineering_content"]
    for di in ec.get("design_inputs", []):
        if di.get("id") == di_id:
            di["value"] = new_value
            print(f"  {pkg_id} {di_id}: updated value to '{new_value[:80]}...'")
            break
    with open(fpath, "w") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)


def fix_build_plan(pkg_id, wp_idx, new_test_article):
    """Update a build plan work package test_article to be package-specific."""
    fpath = os.path.join(OUTPUT_DIR, f"{pkg_id}_ArtifactRichDossier.json")
    with open(fpath) as f:
        dossier = json.load(f)
    ec = dossier["engineering_content"]
    bp = ec.get("engineering_build_plan", [])
    if wp_idx < len(bp):
        if bp[wp_idx].get("test_article", "").startswith("Biocompatibility specimens") or \
           bp[wp_idx].get("test_article", "").startswith("EMC test articles"):
            bp[wp_idx]["test_article"] = new_test_article
            print(f"  {pkg_id} WP[{wp_idx}]: updated test_article to '{new_test_article[:80]}...'")
    with open(fpath, "w") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)


def fix_remaining_unknown(pkg_id, old_text_prefix, new_text):
    """Update a remaining_unknown entry to be package-specific."""
    fpath = os.path.join(OUTPUT_DIR, f"{pkg_id}_ArtifactRichDossier.json")
    with open(fpath) as f:
        dossier = json.load(f)
    ec = dossier["engineering_content"]
    ru = ec.get("engineering_core", {}).get("remaining_unknowns", [])
    for i, u in enumerate(ru):
        if isinstance(u, str) and u.startswith(old_text_prefix):
            ru[i] = new_text
            print(f"  {pkg_id} remaining_unknown[{i}]: updated to '{new_text[:80]}...'")
            break
    with open(fpath, "w") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)


# Package-specific biocompatibility specimen descriptions
PKG_BIO_SPECIMENS = {
    "P-01": "Biocompatibility specimens (multi-segment silicone catheter + COTS sensor encapsulation)",
    "P-11": "Biocompatibility specimens (Ti-coated catheter coupons + phage K stabilization matrix)",
    "P-15-R1": "Biocompatibility specimens (PVDF piezo film + parylene-C encapsulation)",
    "P-22-R1": "Biocompatibility specimens (Pebax multi-lumen catheter + hydraulic actuator silicone)",
    "P-26": "Biocompatibility specimens (PES membrane + osmotic reservoir housing + NaCl agent)",
    "P-27-R1": "Biocompatibility specimens (MEMS sensor die + Ti canister packaging + catheter body)",
    "P-28": "Biocompatibility specimens (PZT transducer + parylene encapsulation + acoustic window)",
}

# Package-specific EMC test article descriptions
PKG_EMC_SPECIMENS = {
    "P-21-R1": "EMC test articles (UWB TX + implantable antenna + external receiver array)",
    "P-27-R1": "EMC test articles (MEMS sensor + signal conditioning + wireless transmitter)",
    "P-28": "EMC test articles (acoustic transducer + drive/receive electronics + classifier MCU)",
    "P-29": "EMC test articles (miniaturized magnet + RF coil + gradient coil + transceiver)",
}


def main():
    print("FIXING LEAKAGE DETECTOR FINDINGS...")

    # 1. Fix design_inputs duplications
    print("\n[1] Fixing design_inputs duplications...")
    fix_design_inputs("P-07", "DI-003",
        "Laminar, Re << 2300 (multi-lumen parallel flow; per-lumen Re << 2300)")
    fix_design_inputs("P-24", "DI-003" if False else "DI-004",
        "Laminar, Re << 2300 (damper element flow through proportional orifice)")
    fix_design_inputs("P-07", "DI-004",
        "ICP 5-40 mmHg (floor activation threshold range; passive safety engages at high ICP)")
    fix_design_inputs("P-26", "DI-004",
        "ICP 5-40 mmHg (osmotic regulation range; membrane flux responds to combined hydrostatic + osmotic)")

    # 2. Fix build_plan duplications (biocompatibility specimens)
    print("\n[2] Fixing build_plan biocompatibility specimens duplications...")
    for pkg_id, specimen in PKG_BIO_SPECIMENS.items():
        fpath = os.path.join(OUTPUT_DIR, f"{pkg_id}_ArtifactRichDossier.json")
        with open(fpath) as f:
            dossier = json.load(f)
        ec = dossier["engineering_content"]
        bp = ec.get("engineering_build_plan", [])
        modified = False
        for wp in bp:
            ta = wp.get("test_article", "")
            if ta.startswith("Biocompatibility specimens") and ta != specimen:
                wp["test_article"] = specimen
                modified = True
        if modified:
            with open(fpath, "w") as f:
                json.dump(dossier, f, indent=2, ensure_ascii=False)
            print(f"  {pkg_id}: updated biocompatibility test_article")

    # 3. Fix build_plan duplications (EMC test articles)
    print("\n[3] Fixing build_plan EMC test articles duplications...")
    for pkg_id, specimen in PKG_EMC_SPECIMENS.items():
        fpath = os.path.join(OUTPUT_DIR, f"{pkg_id}_ArtifactRichDossier.json")
        with open(fpath) as f:
            dossier = json.load(f)
        ec = dossier["engineering_content"]
        bp = ec.get("engineering_build_plan", [])
        modified = False
        for wp in bp:
            ta = wp.get("test_article", "")
            if ta.startswith("EMC test articles") and ta != specimen:
                wp["test_article"] = specimen
                modified = True
        if modified:
            with open(fpath, "w") as f:
                json.dump(dossier, f, indent=2, ensure_ascii=False)
            print(f"  {pkg_id}: updated EMC test_article")

    # 4. Fix remaining_unknowns duplication
    print("\n[4] Fixing remaining_unknowns duplications...")
    fix_remaining_unknown("P-07",
        "Clinical benefit magnitude",
        "Clinical benefit magnitude for passive safety floor — reduction in obstruction-related revision rate vs standard shunt — UNKNOWN until trial")
    fix_remaining_unknown("P-24",
        "Clinical benefit magnitude",
        "Clinical benefit magnitude for proportional damper — ICP excursion amplitude reduction vs existing ASD — UNKNOWN until comparative trial")
    fix_remaining_unknown("P-26",
        "Clinical benefit magnitude",
        "Clinical benefit magnitude for osmotic regulation — drainage stability vs fixed-pressure valve across CSF osmolarity variation — UNKNOWN until trial")

    print("\nDone. Re-run leakage detector to verify fixes.")


if __name__ == "__main__":
    main()

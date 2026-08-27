"""
r370x_buyer_distribution_fix.py — Final Distribution Fix.

Make DOWNLOAD/ the authoritative buyer distribution layer.
Each package ZIP contains the COMPLETE package (PDFs + JSON + V2 artifacts).
Folder/ZIP equivalence mechanically verified.

Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII.
"""
import json
import os
import hashlib
import shutil
import zipfile
from datetime import datetime, timezone

PORTFOLIO_ROOT = "/home/z/my-project/technology-transfer-portfolio-15"

PACKAGE_MAP = [
    ("01", "P-01", "01_multisegment_flow_control"),
    ("02", "P-02", "02_adaptive_valve"),
    ("03", "P-04", "03_catalytic_clearance"),
    ("04", "P-07", "04_drainage_floor"),
    ("05", "P-11", "05_phage_antibiofilm"),
    ("06", "P-13", "06_failure_predictor"),
    ("07", "P-15-R1", "07_self_powered_sensing"),
    ("08", "P-16", "08_nir_photovoltaic"),
    ("09", "P-21-R1", "09_uwb_localization"),
    ("10", "P-22-R1", "10_catheter_navigation"),
    ("11", "P-24", "11_gravity_damper"),
    ("12", "P-26", "12_osmotic_valve"),
    ("13", "P-27-R1", "13_pressure_sensor"),
    ("14", "P-28", "14_acoustic_detection"),
    ("15", "P-29", "15_mr_flow_sensor"),
]

def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_file(filepath):
    if not os.path.exists(filepath):
        return "NOT_FOUND"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ============================================================================
# Step 1: Create DOWNLOAD/NN_folder/ complete package folders
# ============================================================================

def step1_create_download_folders():
    """Copy complete package contents from FULL_DOSSIERS to DOWNLOAD/NN_folder/"""
    print("\n[Step 1] Creating DOWNLOAD/NN_folder/ complete package folders...")

    download_dir = os.path.join(PORTFOLIO_ROOT, "DOWNLOAD")

    for num, pkg_id, folder in PACKAGE_MAP:
        src_dir = os.path.join(PORTFOLIO_ROOT, "FULL_DOSSIERS", folder)
        dst_dir = os.path.join(download_dir, folder)

        # Remove old folder if exists
        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir)

        # Copy complete package
        shutil.copytree(src_dir, dst_dir)

        # Count files
        file_count = len(os.listdir(dst_dir))
        print(f"  {folder}: {file_count} files copied")

    print(f"  15 complete package folders created in DOWNLOAD/")


# ============================================================================
# Step 2: Create 15 package ZIPs from DOWNLOAD/NN_folder/ folders
# ============================================================================

def step2_create_package_zips():
    """Create ZIPs that exactly match their corresponding DOWNLOAD/NN_folder/."""
    print("\n[Step 2] Creating 15 complete package ZIPs...")

    download_dir = os.path.join(PORTFOLIO_ROOT, "DOWNLOAD")
    zip_hashes = {}

    for num, pkg_id, folder in PACKAGE_MAP:
        folder_path = os.path.join(download_dir, folder)
        zip_path = os.path.join(download_dir, f"{folder}.zip")

        # Remove old ZIP
        if os.path.exists(zip_path):
            os.remove(zip_path)

        # Create ZIP with all files from the folder
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in sorted(os.listdir(folder_path)):
                fpath = os.path.join(folder_path, fname)
                if os.path.isfile(fpath):
                    # Store with folder name as prefix for clean extraction
                    zf.write(fpath, f"{folder}/{fname}")

        zip_hash = sha256_file(zip_path)
        zip_hashes[pkg_id] = zip_hash

        # Count files in ZIP
        with zipfile.ZipFile(zip_path) as zf:
            zip_file_count = len(zf.namelist())

        print(f"  {folder}.zip: {zip_file_count} files, hash={zip_hash[:16]}...")

    return zip_hashes


# ============================================================================
# Step 3: Create master ZIP
# ============================================================================

def step3_create_master_zip(zip_hashes):
    """Create master ZIP containing 15 package ZIPs + index + README + manifest."""
    print("\n[Step 3] Creating master ZIP...")

    download_dir = os.path.join(PORTFOLIO_ROOT, "DOWNLOAD")
    master_zip_path = os.path.join(download_dir, "technology-transfer-portfolio-15.zip")

    # Remove old master ZIP
    if os.path.exists(master_zip_path):
        os.remove(master_zip_path)

    with zipfile.ZipFile(master_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add 15 package ZIPs
        for num, pkg_id, folder in PACKAGE_MAP:
            zip_path = os.path.join(download_dir, f"{folder}.zip")
            zf.write(zip_path, f"{folder}.zip")

        # Add PORTFOLIO_INDEX.pdf
        index_path = os.path.join(PORTFOLIO_ROOT, "PORTFOLIO_INDEX.pdf")
        if os.path.exists(index_path):
            zf.write(index_path, "PORTFOLIO_INDEX.pdf")

        # Add README.md
        readme_path = os.path.join(PORTFOLIO_ROOT, "README.md")
        if os.path.exists(readme_path):
            zf.write(readme_path, "README.md")

        # Add PORTFOLIO_MANIFEST.json
        manifest_path = os.path.join(PORTFOLIO_ROOT, "PORTFOLIO_MANIFEST.json")
        if os.path.exists(manifest_path):
            zf.write(manifest_path, "PORTFOLIO_MANIFEST.json")

    master_hash = sha256_file(master_zip_path)

    # Count contents
    with zipfile.ZipFile(master_zip_path) as zf:
        content_count = len(zf.namelist())

    print(f"  Master ZIP: {content_count} files, hash={master_hash[:16]}...")
    return master_hash


# ============================================================================
# Step 4-5: Update package READMEs with explicit hierarchy
# ============================================================================

def step4_5_update_readmes():
    """Update README.md to state explicit hierarchy and naming."""
    print("\n[Steps 4-5] Updating README with explicit hierarchy...")

    # Update main README.md
    main_readme_path = os.path.join(PORTFOLIO_ROOT, "README.md")
    readme_content = """# Technology Transfer Portfolio — 15 CSF Shunt Technologies

## What This Repository Contains

This repository contains **15 complete engineering technology-transfer packages** for CSF (cerebrospinal fluid) shunt improvement technologies. Each package is a self-contained buyer distribution unit.

## How to Download

### For a Single Technology

Download the individual numbered ZIP for the specific technology:

```
DOWNLOAD/01_multisegment_flow_control.zip
DOWNLOAD/02_adaptive_valve.zip
...
DOWNLOAD/15_mr_flow_sensor.zip
```

**Each ZIP is the complete buyer package for that technology.** It contains:
- 6 PDFs (README, Executive Brief, Engineering Dossier, Buyer Card, Evidence Summary, Transfer Manifest)
- Machine-readable engineering files (PACKAGE_MANIFEST.json, ENGINEERING_TRACEABILITY.json, MATURITY_BASIS.json)
- V2 mutation artifacts (where applicable)

### For the Entire Portfolio

Download:

```
DOWNLOAD/technology-transfer-portfolio-15.zip
```

This master ZIP contains all 15 individual package ZIPs plus the portfolio index and manifest.

## Package Hierarchy (Within Each ZIP)

```
START HERE
    ↓
03_BUYER_DECISION_CARD.pdf          ← Entry point: is this technology for you?

THEN
    ↓
01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf   ← 1-page executive summary

FULL TECHNICAL REVIEW
    ↓
02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf  ← Full Engineering Technology-Transfer Dossier

EVIDENCE
    ↓
04_EVIDENCE_SUMMARY.pdf             ← External evidence sources

TRANSFER SCOPE
    ↓
05_TRANSFER_MANIFEST.pdf            ← What the buyer receives vs must develop
```

## Key Distinction

The **02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf** is the full engineering dossier. The **03_BUYER_DECISION_CARD.pdf** is an entry point — not the dossier.

## Maturity Status

All 15 technologies are at **ENGINEERING_DEFINITION** maturity (TRL 2-3). They are:
- Complete-for-current-stage engineering documentation
- NOT validated technologies
- NOT transfer-ready products
- Pre-prototype concept documentation prepared to a professional standard

## V2 Mutations

8 packages have been updated to V2 based on external consultant audit:
- P-01, P-07: Obstruction rate corrected with population-specific sources
- P-13: "Neuromorphic" terminology corrected to "ML-based (gradient boosting)"
- P-27-R1: Regulatory terminology corrected (GWM = Class II/510(k))
- P-15-R1, P-21-R1, P-28, P-29: HIGH FEASIBILITY RISK disclosures added

7 packages remain at V1 (no mutation warranted).

## Honest Status

```
EXTERNAL_CONSULTANT_ASSESSMENT = INGESTED
AI_LEARNING = VERIFIED
PACKAGE_V2 = GENERATED WHERE WARRANTED
REAL_BUYER = 0
REAL_EXPERIMENT = 0
REAL_DATA = 0
REAL_LOOP_VERIFIED = FALSE
TRANSFER_READY = 0/15
```
"""
    with open(main_readme_path, "w") as f:
        f.write(readme_content)
    print(f"  Main README.md updated")

    # The individual 00_PACKAGE_README.pdf files are pre-generated PDFs.
    # We cannot easily modify PDFs, but the main README.md now provides
    # the explicit hierarchy. The package structure itself makes the
    # hierarchy clear through numbering.


# ============================================================================
# Step 6: Verify ZIP-folder equivalence
# ============================================================================

def step6_verify_equivalence():
    """Verify that ZIP contents exactly match folder contents for all 15 packages."""
    print("\n[Step 6] Verifying ZIP-folder equivalence...")

    download_dir = os.path.join(PORTFOLIO_ROOT, "DOWNLOAD")
    all_pass = True
    results = []

    for num, pkg_id, folder in PACKAGE_MAP:
        folder_path = os.path.join(download_dir, folder)
        zip_path = os.path.join(download_dir, f"{folder}.zip")

        # Get folder files (with folder/ prefix for comparison)
        folder_files = set()
        for fname in os.listdir(folder_path):
            if os.path.isfile(os.path.join(folder_path, fname)):
                folder_files.add(f"{folder}/{fname}")

        # Get ZIP contents
        with zipfile.ZipFile(zip_path) as zf:
            zip_files = set(zf.namelist())

        # Compare
        if folder_files == zip_files:
            # Verify hashes match
            hash_mismatches = 0
            with zipfile.ZipFile(zip_path) as zf:
                for fname in os.listdir(folder_path):
                    fpath = os.path.join(folder_path, fname)
                    if os.path.isfile(fpath):
                        folder_hash = sha256_file(fpath)
                        zip_entry = f"{folder}/{fname}"
                        try:
                            zip_data = zf.read(zip_entry)
                            zip_hash = hashlib.sha256(zip_data).hexdigest()
                            if folder_hash != zip_hash:
                                hash_mismatches += 1
                        except KeyError:
                            hash_mismatches += 1

            if hash_mismatches == 0:
                results.append({"package": pkg_id, "folder": folder, "verdict": "PASS",
                                "file_count": len(folder_files)})
                print(f"  PASS: {folder} — {len(folder_files)} files, all hashes match")
            else:
                results.append({"package": pkg_id, "folder": folder, "verdict": "FAIL",
                                "reason": f"{hash_mismatches} hash mismatches"})
                print(f"  FAIL: {folder} — {hash_mismatches} hash mismatches")
                all_pass = False
        else:
            only_in_folder = folder_files - zip_files
            only_in_zip = zip_files - folder_files
            results.append({"package": pkg_id, "folder": folder, "verdict": "FAIL",
                            "only_in_folder": list(only_in_folder),
                            "only_in_zip": list(only_in_zip)})
            print(f"  FAIL: {folder} — folder/ZIP mismatch")
            if only_in_folder:
                print(f"    Only in folder: {only_in_folder}")
            if only_in_zip:
                print(f"    Only in ZIP: {only_in_zip}")
            all_pass = False

    print(f"\n  {'ALL 15 PACKAGES PASS' if all_pass else 'FAILURES DETECTED'}")
    return all_pass, results


# ============================================================================
# Step 7: Create BUYER_DISTRIBUTION_RELEASE_CERTIFICATE.json
# ============================================================================

def step7_create_release_certificate(zip_hashes, master_hash, equivalence_results):
    """Create release certificate with all package hashes."""
    print("\n[Step 7] Creating BUYER_DISTRIBUTION_RELEASE_CERTIFICATE.json...")

    packages = []
    for num, pkg_id, folder in PACKAGE_MAP:
        folder_path = os.path.join(PORTFOLIO_ROOT, "DOWNLOAD", folder)
        dossier_dir = os.path.join(PORTFOLIO_ROOT, "FULL_DOSSIERS", folder)

        # Load package manifest to get version
        pm_path = os.path.join(dossier_dir, "PACKAGE_MANIFEST.json")
        with open(pm_path) as f:
            pm = json.load(f)
        version = pm.get("package_version", "1.0")

        # Hash all files in the folder
        folder_files = {}
        for fname in sorted(os.listdir(folder_path)):
            fpath = os.path.join(folder_path, fname)
            if os.path.isfile(fpath):
                folder_files[fname] = sha256_file(fpath)

        # Compute folder hash (hash of all file hashes concatenated)
        folder_hash = sha256_str(json.dumps(folder_files, sort_keys=True))

        packages.append({
            "portfolio_number": num,
            "package_id": pkg_id,
            "folder_name": folder,
            "version": version,
            "folder_hash": folder_hash,
            "zip_hash": zip_hashes.get(pkg_id, "NOT_FOUND"),
            "file_hashes": folder_files,
            "equivalence_verified": next((r["verdict"] for r in equivalence_results if r["package"] == pkg_id), "NOT_CHECKED"),
        })

    certificate = {
        "certificate_type": "BUYER_DISTRIBUTION_RELEASE_CERTIFICATE",
        "version": "1.0",
        "generated_at": _now(),
        "package_count": 15,
        "master_zip_hash": master_hash,
        "packages": packages,
        "distribution_structure": {
            "canonical_download_path": "DOWNLOAD/",
            "individual_zips": "DOWNLOAD/NN_folder_name.zip",
            "master_zip": "DOWNLOAD/technology-transfer-portfolio-15.zip",
            "individual_folders": "DOWNLOAD/NN_folder_name/",
            "full_dossiers": "FULL_DOSSIERS/NN_folder_name/ (source for DOWNLOAD/)",
        },
        "hierarchy_documented": True,
        "honest_status": {
            "EXTERNAL_CONSULTANT_ASSESSMENT": "INGESTED",
            "AI_LEARNING": "VERIFIED",
            "PACKAGE_V2": "GENERATED WHERE WARRANTED",
            "REAL_BUYER": 0,
            "REAL_EXPERIMENT": 0,
            "REAL_DATA": 0,
            "REAL_LOOP_VERIFIED": "FALSE",
            "TRANSFER_READY": "0/15",
        },
    }

    # Compute self_hash
    obj_for_hash = {k: v for k, v in certificate.items() if k != "self_hash"}
    certificate["self_hash"] = sha256_str(json.dumps(obj_for_hash, sort_keys=True, ensure_ascii=False))

    # Save
    release_dir = os.path.join(PORTFOLIO_ROOT, "RELEASE")
    os.makedirs(release_dir, exist_ok=True)
    cert_path = os.path.join(release_dir, "BUYER_DISTRIBUTION_RELEASE_CERTIFICATE.json")
    with open(cert_path, "w") as f:
        json.dump(certificate, f, indent=2, ensure_ascii=False)

    # Also save at root for visibility
    root_cert_path = os.path.join(PORTFOLIO_ROOT, "BUYER_DISTRIBUTION_RELEASE_CERTIFICATE.json")
    with open(root_cert_path, "w") as f:
        json.dump(certificate, f, indent=2, ensure_ascii=False)

    print(f"  Certificate saved: {cert_path}")
    print(f"  Also at: {root_cert_path}")
    print(f"  Self hash: {certificate['self_hash'][:16]}...")
    return certificate


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("R370X BUYER DISTRIBUTION FIX")
    print("Make DOWNLOAD/ the authoritative buyer distribution layer")
    print("=" * 70)

    # Step 1: Create complete package folders in DOWNLOAD/
    step1_create_download_folders()

    # Step 2: Create 15 complete package ZIPs
    zip_hashes = step2_create_package_zips()

    # Step 3: Create master ZIP
    master_hash = step3_create_master_zip(zip_hashes)

    # Steps 4-5: Update READMEs
    step4_5_update_readmes()

    # Step 6: Verify ZIP-folder equivalence
    equivalence_pass, equivalence_results = step6_verify_equivalence()

    # Step 7: Create release certificate
    certificate = step7_create_release_certificate(zip_hashes, master_hash, equivalence_results)

    # Final summary
    print(f"\n{'='*70}")
    print(f"BURDER DISTRIBUTION FIX COMPLETE")
    print(f"{'='*70}")
    print(f"\n  15 complete package folders in DOWNLOAD/")
    print(f"  15 complete package ZIPs (each contains full package)")
    print(f"  1 master ZIP (contains 15 package ZIPs + index + README + manifest)")
    print(f"  ZIP-folder equivalence: {'15/15 PASS' if equivalence_pass else 'FAIL'}")
    print(f"  Release certificate: generated")
    print(f"\n  Distribution structure:")
    print(f"    DOWNLOAD/NN_folder_name/     ← complete package folder")
    print(f"    DOWNLOAD/NN_folder_name.zip  ← complete package ZIP")
    print(f"    DOWNLOAD/technology-transfer-portfolio-15.zip ← master ZIP")
    print(f"\n  STOP. Buyer distribution is now unambiguous.")

    return 0 if equivalence_pass else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())

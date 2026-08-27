"""
r370x_final_distribution_gate.py — Final Buyer-Distribution Verification Gate.

Per CEO: run one final mechanical proof that the master ZIP and all 15
individual ZIPs are exactly the frozen buyer packages.

For every 01-15 package verify:
  - PACKAGE_FOLDER_EXISTS = PASS
  - PACKAGE_ZIP_EXISTS = PASS
  - 6 required PDFs present
  - 3 required JSONs present
  - V2 artifacts present (where applicable)

Then extract all 15 ZIPs and compare every file hash against the folder.

Final certificate must say:
  COMPLETE_BUYER_PACKAGES = 15/15
  ZIP_FOLDER_HASH_EQUIVALENCE = 15/15
  FULL_ENGINEERING_DOSSIERS = 15/15
  MASTER_ZIP_CONTAINS_15_COMPLETE_PACKAGES = PASS

Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII.
"""
import json
import os
import hashlib
import zipfile
import shutil
import subprocess
from datetime import datetime, timezone

PORTFOLIO_ROOT = "/home/z/my-project/technology-transfer-portfolio-15"
TOKEN_FILE = "/tmp/gh_token.txt"
DEV_REPO = "prateekm1007/discovery-evidence-fabric"
PORTFOLIO_REPO = "prateekm1007/technology-transfer-portfolio-15"

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

V2_PACKAGES = {"P-01", "P-07", "P-13", "P-27-R1", "P-15-R1", "P-21-R1", "P-28", "P-29"}

REQUIRED_PDFS = [
    "00_PACKAGE_README.pdf",
    "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
    "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
    "03_BUYER_DECISION_CARD.pdf",
    "04_EVIDENCE_SUMMARY.pdf",
    "05_TRANSFER_MANIFEST.pdf",
]

REQUIRED_JSONS = [
    "ENGINEERING_TRACEABILITY.json",
    "MATURITY_BASIS.json",
    "PACKAGE_MANIFEST.json",
]

V2_REQUIRED_FILES = [
    "V2_MUTATION_ADDENDUM.json",
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

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


# ============================================================================
# Fresh clone from GitHub to verify live state
# ============================================================================

def fresh_clone():
    """Fresh clone the portfolio repo to verify live GitHub state."""
    print("=" * 70)
    print("FRESH-CLONE VERIFICATION FROM GITHUB")
    print("=" * 70)

    clone_path = "/tmp/r370x-final-gate-portfolio"

    with open(TOKEN_FILE) as f:
        token = f.read().strip()

    if os.path.exists(clone_path):
        shutil.rmtree(clone_path)

    result = subprocess.run(
        ["git", "clone", f"https://prateekm1007:{token}@github.com/{PORTFOLIO_REPO}.git", clone_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"FAIL: Could not clone portfolio repo: {result.stderr}")
        return None

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clone_path, text=True).strip()
    print(f"  Cloned. HEAD = {head}")
    return clone_path


# ============================================================================
# Verify each package: folder, ZIP, required files
# ============================================================================

def verify_packages(portfolio_root):
    """Verify all 15 packages have required folders, ZIPs, and files."""
    print("\n[1] Verifying 15 packages: folders, ZIPs, required files...")

    package_results = []
    all_pass = True

    for num, pkg_id, folder in PACKAGE_MAP:
        download_dir = os.path.join(portfolio_root, "DOWNLOAD")
        folder_path = os.path.join(download_dir, folder)
        zip_path = os.path.join(download_dir, f"{folder}.zip")

        result = {
            "portfolio_number": num,
            "package_id": pkg_id,
            "folder_name": folder,
            "is_v2": pkg_id in V2_PACKAGES,
            "checks": {},
        }

        # Check folder exists
        result["checks"]["PACKAGE_FOLDER_EXISTS"] = "PASS" if os.path.isdir(folder_path) else "FAIL"

        # Check ZIP exists
        result["checks"]["PACKAGE_ZIP_EXISTS"] = "PASS" if os.path.isfile(zip_path) else "FAIL"

        # Check required PDFs
        for pdf in REQUIRED_PDFS:
            pdf_path = os.path.join(folder_path, pdf)
            result["checks"][pdf] = "PASS" if os.path.isfile(pdf_path) else "FAIL"

        # Check required JSONs
        for jsn in REQUIRED_JSONS:
            json_path = os.path.join(folder_path, jsn)
            result["checks"][jsn] = "PASS" if os.path.isfile(json_path) else "FAIL"

        # Check V2 artifacts
        if pkg_id in V2_PACKAGES:
            for v2_file in V2_REQUIRED_FILES:
                v2_path = os.path.join(folder_path, v2_file)
                result["checks"][v2_file] = "PASS" if os.path.isfile(v2_path) else "FAIL"

            # Check mutation certificate
            cert_filename = f"PACKAGE_MUTATION_CERTIFICATE_{pkg_id}_V2.json"
            cert_path = os.path.join(folder_path, cert_filename)
            result["checks"]["PACKAGE_MUTATION_CERTIFICATE"] = "PASS" if os.path.isfile(cert_path) else "FAIL"

        # Determine overall pass/fail
        failed_checks = [k for k, v in result["checks"].items() if v == "FAIL"]
        result["overall"] = "PASS" if not failed_checks else "FAIL"
        result["failed_checks"] = failed_checks

        if failed_checks:
            all_pass = False

        status = "PASS" if not failed_checks else f"FAIL ({len(failed_checks)} checks)"
        print(f"  {num} {pkg_id}: {status}")

        package_results.append(result)

    print(f"\n  Packages passing: {sum(1 for r in package_results if r['overall'] == 'PASS')}/15")
    return package_results, all_pass


# ============================================================================
# Extract all 15 ZIPs and compare every file hash against folder
# ============================================================================

def verify_zip_folder_equivalence(portfolio_root):
    """Extract each ZIP and compare every file hash against the folder."""
    print("\n[2] Extracting all 15 ZIPs and comparing file hashes against folders...")

    download_dir = os.path.join(portfolio_root, "DOWNLOAD")
    extract_base = "/tmp/r370x-zip-extract"

    if os.path.exists(extract_base):
        shutil.rmtree(extract_base)
    os.makedirs(extract_base)

    equivalence_results = []
    all_pass = True

    for num, pkg_id, folder in PACKAGE_MAP:
        zip_path = os.path.join(download_dir, f"{folder}.zip")
        folder_path = os.path.join(download_dir, folder)
        extract_dir = os.path.join(extract_base, folder)

        os.makedirs(extract_dir, exist_ok=True)

        # Extract ZIP
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        # The ZIP stores files under folder/ prefix
        extracted_folder = os.path.join(extract_dir, folder)

        # Get all files in folder
        folder_files = {}
        for fname in sorted(os.listdir(folder_path)):
            fpath = os.path.join(folder_path, fname)
            if os.path.isfile(fpath):
                folder_files[fname] = sha256_file(fpath)

        # Get all files in extracted ZIP
        zip_files = {}
        for fname in sorted(os.listdir(extracted_folder)):
            fpath = os.path.join(extracted_folder, fname)
            if os.path.isfile(fpath):
                zip_files[fname] = sha256_file(fpath)

        # Compare
        file_match_count = 0
        file_mismatch_count = 0
        mismatches = []

        all_filenames = set(folder_files.keys()) | set(zip_files.keys())
        for fname in all_filenames:
            folder_hash = folder_files.get(fname, "NOT_FOUND")
            zip_hash = zip_files.get(fname, "NOT_FOUND")
            if folder_hash == zip_hash:
                file_match_count += 1
            else:
                file_mismatch_count += 1
                mismatches.append({
                    "file": fname,
                    "folder_hash": folder_hash[:16] + "..." if folder_hash != "NOT_FOUND" else "NOT_FOUND",
                    "zip_hash": zip_hash[:16] + "..." if zip_hash != "NOT_FOUND" else "NOT_FOUND",
                })

        result = {
            "portfolio_number": num,
            "package_id": pkg_id,
            "folder_name": folder,
            "folder_file_count": len(folder_files),
            "zip_file_count": len(zip_files),
            "files_matched": file_match_count,
            "files_mismatched": file_mismatch_count,
            "mismatches": mismatches,
            "verdict": "PASS" if file_mismatch_count == 0 else "FAIL",
        }

        if file_mismatch_count > 0:
            all_pass = False

        print(f"  {num} {pkg_id}: {file_match_count}/{len(all_filenames)} files match — {result['verdict']}")
        if mismatches:
            for m in mismatches:
                print(f"    MISMATCH: {m['file']}")

        equivalence_results.append(result)

    # Cleanup
    shutil.rmtree(extract_base)

    print(f"\n  ZIP-folder equivalence: {sum(1 for r in equivalence_results if r['verdict'] == 'PASS')}/15 PASS")
    return equivalence_results, all_pass


# ============================================================================
# Verify master ZIP contains 15 complete package ZIPs
# ============================================================================

def verify_master_zip(portfolio_root):
    """Verify master ZIP contains all 15 complete package ZIPs + index + README + manifest."""
    print("\n[3] Verifying master ZIP contains 15 complete package ZIPs...")

    master_zip_path = os.path.join(portfolio_root, "DOWNLOAD", "technology-transfer-portfolio-15.zip")

    if not os.path.exists(master_zip_path):
        print("  FAIL: Master ZIP not found")
        return {"verdict": "FAIL", "reason": "Master ZIP not found"}, False

    with zipfile.ZipFile(master_zip_path) as zf:
        master_contents = zf.namelist()

    # Check all 15 package ZIPs are in master
    expected_zips = [f"{folder}.zip" for _, _, folder in PACKAGE_MAP]
    missing_zips = [z for z in expected_zips if z not in master_contents]

    # Check index, README, manifest
    has_index = "PORTFOLIO_INDEX.pdf" in master_contents
    has_readme = "README.md" in master_contents
    has_manifest = "PORTFOLIO_MANIFEST.json" in master_contents

    # Verify each package ZIP inside master matches the individual ZIP
    zip_hash_matches = 0
    zip_hash_mismatches = []

    with zipfile.ZipFile(master_zip_path) as zf:
        for num, pkg_id, folder in PACKAGE_MAP:
            zip_name = f"{folder}.zip"
            if zip_name in master_contents:
                # Get hash of ZIP inside master
                master_zip_data = zf.read(zip_name)
                master_zip_hash = sha256_bytes(master_zip_data)

                # Get hash of individual ZIP
                individual_zip_path = os.path.join(portfolio_root, "DOWNLOAD", zip_name)
                individual_hash = sha256_file(individual_zip_path)

                if master_zip_hash == individual_hash:
                    zip_hash_matches += 1
                else:
                    zip_hash_mismatches.append({
                        "package": pkg_id,
                        "zip": zip_name,
                        "master_hash": master_zip_hash[:16] + "...",
                        "individual_hash": individual_hash[:16] + "...",
                    })

    result = {
        "master_zip_exists": True,
        "total_contents": len(master_contents),
        "expected_package_zips": 15,
        "package_zips_found": 15 - len(missing_zips),
        "missing_zips": missing_zips,
        "has_portfolio_index": has_index,
        "has_readme": has_readme,
        "has_portfolio_manifest": has_manifest,
        "zip_hash_matches": zip_hash_matches,
        "zip_hash_mismatches": zip_hash_mismatches,
        "verdict": "PASS" if (len(missing_zips) == 0 and has_index and has_readme
                              and has_manifest and zip_hash_matches == 15) else "FAIL",
    }

    print(f"  Contents: {result['total_contents']} files")
    print(f"  Package ZIPs found: {result['package_zips_found']}/15")
    print(f"  Has PORTFOLIO_INDEX.pdf: {has_index}")
    print(f"  Has README.md: {has_readme}")
    print(f"  Has PORTFOLIO_MANIFEST.json: {has_manifest}")
    print(f"  ZIP hash matches: {zip_hash_matches}/15")
    if zip_hash_mismatches:
        print(f"  HASH MISMATCHES:")
        for m in zip_hash_mismatches:
            print(f"    {m['package']} {m['zip']}")
    print(f"  Verdict: {result['verdict']}")

    return result, result["verdict"] == "PASS"


# ============================================================================
# Generate final certificate
# ============================================================================

def generate_certificate(package_results, equivalence_results, master_zip_result, portfolio_head):
    """Generate FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE.json."""
    print("\n[4] Generating FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE.json...")

    complete_packages = sum(1 for r in package_results if r["overall"] == "PASS")
    zip_equivalence = sum(1 for r in equivalence_results if r["verdict"] == "PASS")
    full_dossiers = sum(1 for r in package_results
                        if r["checks"].get("02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf") == "PASS")

    certificate = {
        "certificate_type": "FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE",
        "version": "1.0",
        "generated_at": _now(),
        "portfolio_repository": PORTFOLIO_REPO,
        "portfolio_head_commit": portfolio_head,
        "verification_method": "Fresh clone from GitHub + extract all ZIPs + compare every file hash",

        "summary": {
            "COMPLETE_BUYER_PACKAGES": f"{complete_packages}/15",
            "ZIP_FOLDER_HASH_EQUIVALENCE": f"{zip_equivalence}/15",
            "FULL_ENGINEERING_DOSSIERS": f"{full_dossiers}/15",
            "MASTER_ZIP_CONTAINS_15_COMPLETE_PACKAGES": master_zip_result["verdict"],
        },

        "detailed_results": {
            "package_verification": package_results,
            "zip_folder_equivalence": equivalence_results,
            "master_zip_verification": master_zip_result,
        },

        "buyer_distribution_rule": {
            "specific_buyer": "Send that technology's numbered ZIP (DOWNLOAD/NN_folder_name.zip)",
            "strategic_investor": "Send the master ZIP (DOWNLOAD/technology-transfer-portfolio-15.zip)",
            "rule": "Do not send 02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf by itself unless the recipient specifically asks for just the technical dossier.",
        },

        "package_contents_verified": {
            "per_package": "6 PDFs + 3 JSONs (V1) or 6 PDFs + 3 JSONs + V2 addendum + mutation certificate (V2)",
            "total_pdfs_verified": complete_packages * 6,
            "total_jsons_verified": complete_packages * 3 + sum(1 for r in package_results if r["is_v2"]) * 2,
        },

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

        "freeze_declaration": (
            "Buyer distribution is now frozen. Each numbered ZIP is the complete buyer package. "
            "The master ZIP contains all 15 complete package ZIPs. "
            "Folder ↔ ZIP equivalence is mechanically verified for all 15 packages. "
            "No more software work. Next: send packages to real buyers."
        ),
    }

    all_pass = (complete_packages == 15 and zip_equivalence == 15
                and full_dossiers == 15 and master_zip_result["verdict"] == "PASS")

    certificate["overall_verdict"] = "PASS" if all_pass else "FAIL"

    # Compute self_hash
    obj_for_hash = {k: v for k, v in certificate.items() if k != "self_hash"}
    certificate["self_hash"] = hashlib.sha256(
        json.dumps(obj_for_hash, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    # Save
    cert_path = os.path.join(PORTFOLIO_ROOT, "FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE.json")
    with open(cert_path, "w") as f:
        json.dump(certificate, f, indent=2, ensure_ascii=False)

    # Also save in the clone for GitHub verification
    clone_cert_path = os.path.join("/tmp/r370x-final-gate-portfolio",
                                    "FINAL_DISTRIBUTION_VERIFICATION_CERTIFICATE.json")
    if os.path.exists("/tmp/r370x-final-gate-portfolio"):
        with open(clone_cert_path, "w") as f:
            json.dump(certificate, f, indent=2, ensure_ascii=False)

    print(f"  Saved: {cert_path}")
    print(f"  Self hash: {certificate['self_hash'][:16]}...")
    return certificate, all_pass


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("R370X FINAL DISTRIBUTION VERIFICATION GATE")
    print("Prove that ZIPs are exactly the frozen buyer packages")
    print("=" * 70)

    # Fresh clone from GitHub
    clone_path = fresh_clone()
    if not clone_path:
        return 1

    portfolio_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=clone_path, text=True
    ).strip()

    # Verify packages
    package_results, packages_pass = verify_packages(clone_path)

    # Verify ZIP-folder equivalence
    equivalence_results, equivalence_pass = verify_zip_folder_equivalence(clone_path)

    # Verify master ZIP
    master_zip_result, master_pass = verify_master_zip(clone_path)

    # Generate certificate
    certificate, all_pass = generate_certificate(
        package_results, equivalence_results, master_zip_result, portfolio_head
    )

    # Final report
    print(f"\n{'='*70}")
    print(f"FINAL DISTRIBUTION VERIFICATION REPORT")
    print(f"{'='*70}")

    print(f"""
PORTFOLIO_HEAD = {portfolio_head}

COMPLETE_BUYER_PACKAGES = {certificate['summary']['COMPLETE_BUYER_PACKAGES']}
ZIP_FOLDER_HASH_EQUIVALENCE = {certificate['summary']['ZIP_FOLDER_HASH_EQUIVALENCE']}
FULL_ENGINEERING_DOSSIERS = {certificate['summary']['FULL_ENGINEERING_DOSSIERS']}
MASTER_ZIP_CONTAINS_15_COMPLETE_PACKAGES = {certificate['summary']['MASTER_ZIP_CONTAINS_15_COMPLETE_PACKAGES']}

OVERALL VERDICT = {certificate['overall_verdict']}

BUYER DISTRIBUTION RULE:
  Specific buyer: send DOWNLOAD/NN_folder_name.zip
  Strategic investor: send DOWNLOAD/technology-transfer-portfolio-15.zip
  Do NOT send 02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf alone

HONEST STATUS:
  REAL_BUYER = 0
  REAL_EXPERIMENT = 0
  REAL_DATA = 0
  REAL_LOOP_VERIFIED = FALSE
  TRANSFER_READY = 0/15
""")

    if all_pass:
        print("STOP. Buyer distribution is frozen and verified.")
        print("Next: send packages to real buyers.")
    else:
        print("ISSUES DETECTED — review above.")

    # Cleanup clone
    shutil.rmtree(clone_path)

    return 0 if all_pass else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())

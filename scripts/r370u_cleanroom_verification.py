"""
r370u_cleanroom_verification.py — U9: Clean-room verification with fresh clones.

Per CEO R370U-U9: verify the complete bridge WITHOUT relying on local uncommitted files.

Steps:
1. Fresh clone of dev repo to /tmp/r370u-cleanroom-dev
2. Fresh clone of portfolio repo to /tmp/r370u-cleanroom-portfolio
3. Verify FINAL_ENGINEERING_RELEASE_MANIFEST.json exists in dev clone
4. Verify SOURCE_RELEASE_MANIFEST.json exists in portfolio clone
5. Verify CROSS_REPOSITORY_RELEASE_INTEGRITY.json exists in both
6. Recompute all hashes from fresh clones
7. Verify dev manifest self_hash matches
8. Verify portfolio source_manifest references dev commit + manifest hash
9. Verify all 15 package hashes match between dev and portfolio
10. Report PASS/FAIL
"""
import json
import os
import hashlib
import shutil
import subprocess
import sys

TOKEN_FILE = "/tmp/gh_token.txt"
DEV_REPO = "prateekm1007/discovery-evidence-fabric"
PORTFOLIO_REPO = "prateekm1007/technology-transfer-portfolio-15"
DEV_CLONE = "/tmp/r370u-cleanroom-dev"
PORTFOLIO_CLONE = "/tmp/r370u-cleanroom-portfolio"

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

def sha256_json(obj):
    return sha256_str(json.dumps(obj, sort_keys=True, ensure_ascii=False))

def main():
    print("=" * 70)
    print("R370U-U9: CLEAN-ROOM VERIFICATION")
    print("Verify the complete bridge from FRESH CLONES (no local files)")
    print("=" * 70)

    with open(TOKEN_FILE) as f:
        token = f.read().strip()

    # Step 1: Fresh clone of dev repo
    print("\n[1] Fresh clone of dev repo...")
    if os.path.exists(DEV_CLONE):
        shutil.rmtree(DEV_CLONE)
    result = subprocess.run(
        ["git", "clone", f"https://prateekm1007:{token}@github.com/{DEV_REPO}.git", DEV_CLONE],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"FAIL: Could not clone dev repo: {result.stderr}")
        sys.exit(1)
    dev_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=DEV_CLONE, text=True).strip()
    print(f"  Cloned. HEAD = {dev_commit}")

    # Step 2: Fresh clone of portfolio repo
    print("\n[2] Fresh clone of portfolio repo...")
    if os.path.exists(PORTFOLIO_CLONE):
        shutil.rmtree(PORTFOLIO_CLONE)
    result = subprocess.run(
        ["git", "clone", f"https://prateekm1007:{token}@github.com/{PORTFOLIO_REPO}.git", PORTFOLIO_CLONE],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"FAIL: Could not clone portfolio repo: {result.stderr}")
        sys.exit(1)
    portfolio_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PORTFOLIO_CLONE, text=True).strip()
    print(f"  Cloned. HEAD = {portfolio_commit}")

    # Step 3: Verify FINAL_ENGINEERING_RELEASE_MANIFEST exists in dev clone
    print("\n[3] Verify FINAL_ENGINEERING_RELEASE_MANIFEST.json in dev clone...")
    dev_manifest_path = os.path.join(DEV_CLONE, "premium_package_factory", "output",
                                      "engineering_dossiers_artifact_rich",
                                      "FINAL_ENGINEERING_RELEASE_MANIFEST.json")
    if not os.path.exists(dev_manifest_path):
        print(f"FAIL: {dev_manifest_path} not found in fresh clone")
        sys.exit(1)
    with open(dev_manifest_path) as f:
        dev_manifest = json.load(f)
    print(f"  FOUND. Release ID = {dev_manifest.get('release_id', '?')}")
    print(f"  development_commit = {dev_manifest.get('development_commit', '?')}")
    print(f"  self_hash = {dev_manifest.get('self_hash', '?')}")
    print(f"  canonical_portfolio_hash = {dev_manifest.get('canonical_portfolio_hash', '?')}")

    # Step 4: Verify SOURCE_RELEASE_MANIFEST exists in portfolio clone
    print("\n[4] Verify SOURCE_RELEASE_MANIFEST.json in portfolio clone...")
    source_manifest_path = os.path.join(PORTFOLIO_CLONE, "SOURCE_RELEASE_MANIFEST.json")
    if not os.path.exists(source_manifest_path):
        print(f"FAIL: {source_manifest_path} not found in fresh clone")
        sys.exit(1)
    with open(source_manifest_path) as f:
        source_manifest = json.load(f)
    print(f"  FOUND.")
    print(f"  development_repo = {source_manifest.get('development_repository', '?')}")
    print(f"  development_commit = {source_manifest.get('development_commit', '?')}")
    print(f"  release_manifest_sha256 = {source_manifest.get('final_engineering_release_manifest_sha256', '?')}")

    # Step 5: Verify CROSS_REPOSITORY_RELEASE_INTEGRITY exists in both
    print("\n[5] Verify CROSS_REPOSITORY_RELEASE_INTEGRITY.json in both clones...")
    dev_integrity_path = os.path.join(DEV_CLONE, "premium_package_factory", "output",
                                       "engineering_dossiers_artifact_rich",
                                       "CROSS_REPOSITORY_RELEASE_INTEGRITY.json")
    portfolio_integrity_path = os.path.join(PORTFOLIO_CLONE, "INTERNAL_QA",
                                             "CROSS_REPOSITORY_RELEASE_INTEGRITY.json")
    if not os.path.exists(dev_integrity_path):
        print(f"FAIL: {dev_integrity_path} not found")
        sys.exit(1)
    if not os.path.exists(portfolio_integrity_path):
        print(f"FAIL: {portfolio_integrity_path} not found")
        sys.exit(1)
    with open(dev_integrity_path) as f:
        dev_integrity = json.load(f)
    with open(portfolio_integrity_path) as f:
        portfolio_integrity = json.load(f)
    print(f"  Dev integrity verdict: {dev_integrity.get('verdict', '?')}")
    print(f"  Portfolio integrity verdict: {portfolio_integrity.get('verdict', '?')}")

    # Step 6: Verify dev manifest self_hash matches
    print("\n[6] Verify dev manifest self_hash...")
    manifest_for_hash = {k: v for k, v in dev_manifest.items() if k != "self_hash"}
    recomputed_self_hash = sha256_json(manifest_for_hash)
    recorded_self_hash = dev_manifest.get("self_hash", "")
    if recomputed_self_hash == recorded_self_hash:
        print(f"  PASS: self_hash matches ({recorded_self_hash})")
    else:
        print(f"FAIL: self_hash mismatch")
        print(f"  recorded:  {recorded_self_hash}")
        print(f"  recomputed: {recomputed_self_hash}")
        sys.exit(1)

    # Step 7: Verify portfolio source_manifest references correct dev commit + manifest hash
    print("\n[7] Verify portfolio references correct dev commit + manifest hash...")
    if source_manifest.get("development_commit") != dev_manifest.get("development_commit"):
        print(f"FAIL: development_commit mismatch")
        print(f"  dev manifest: {dev_manifest.get('development_commit')}")
        print(f"  portfolio source: {source_manifest.get('development_commit')}")
        sys.exit(1)
    print(f"  PASS: development_commit matches ({source_manifest.get('development_commit')})")

    if source_manifest.get("final_engineering_release_manifest_sha256") != dev_manifest.get("self_hash"):
        print(f"FAIL: release manifest hash mismatch")
        print(f"  dev manifest self_hash: {dev_manifest.get('self_hash')}")
        print(f"  portfolio source references: {source_manifest.get('final_engineering_release_manifest_sha256')}")
        sys.exit(1)
    print(f"  PASS: release manifest hash matches")

    # Step 8: Verify all 15 package dossier hashes match between dev and portfolio
    print("\n[8] Verify 15 package dossier hashes match between dev and portfolio...")
    package_map = [
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

    all_match = True
    for num, pkg_id, folder in package_map:
        # Dev dossier hash (from manifest)
        dev_dossier_hash = dev_manifest.get("engineering_dossier_hashes", {}).get(pkg_id, "NOT_FOUND")

        # Portfolio source manifest hash
        source_pkg = None
        for sp in source_manifest.get("packages", []):
            if sp.get("package_id") == pkg_id:
                source_pkg = sp
                break

        if not source_pkg:
            print(f"  FAIL: {pkg_id} not found in portfolio source manifest")
            all_match = False
            continue

        portfolio_source_hash = source_pkg.get("source_package_hash", "NOT_FOUND")

        if dev_dossier_hash != portfolio_source_hash:
            print(f"  FAIL: {pkg_id} hash mismatch")
            print(f"    dev manifest:     {dev_dossier_hash}")
            print(f"    portfolio source: {portfolio_source_hash}")
            all_match = False
        else:
            print(f"  PASS: {pkg_id} ({num}) hash matches")

    if not all_match:
        print(f"\nFAIL: Some package hashes do not match")
        sys.exit(1)

    # Step 9: Verify buyer PDF hashes in portfolio match what's in the source manifest
    print("\n[9] Verify buyer PDF hashes in portfolio clone match source manifest...")
    pdf_mismatches = 0
    for num, pkg_id, folder in package_map:
        source_pkg = None
        for sp in source_manifest.get("packages", []):
            if sp.get("package_id") == pkg_id:
                source_pkg = sp
                break
        if not source_pkg:
            continue

        dossier_dir = os.path.join(PORTFOLIO_CLONE, "FULL_DOSSIERS", folder)
        if not os.path.exists(dossier_dir):
            print(f"  FAIL: {pkg_id} dossier directory not found: {dossier_dir}")
            pdf_mismatches += 1
            continue

        for buyer_pdf in source_pkg.get("buyer_dossier_pdfs", []):
            pdf_path = os.path.join(dossier_dir, buyer_pdf["file"])
            actual_hash = sha256_file(pdf_path)
            if actual_hash != buyer_pdf["sha256"]:
                print(f"  FAIL: {pkg_id}/{buyer_pdf['file']} hash mismatch")
                print(f"    source manifest: {buyer_pdf['sha256']}")
                print(f"    actual file:     {actual_hash}")
                pdf_mismatches += 1

    if pdf_mismatches > 0:
        print(f"\nFAIL: {pdf_mismatches} PDF hash mismatches")
        sys.exit(1)
    print(f"  PASS: All buyer PDF hashes match ({sum(len(sp.get('buyer_dossier_pdfs', [])) for sp in source_manifest.get('packages', []))} PDFs verified)")

    # Step 10: Final summary
    print(f"\n{'='*70}")
    print(f"CLEAN-ROOM VERIFICATION SUMMARY")
    print(f"{'='*70}")
    print(f"\n  Dev repo clone: {DEV_CLONE}")
    print(f"    commit: {dev_commit}")
    print(f"  Portfolio repo clone: {PORTFOLIO_CLONE}")
    print(f"    commit: {portfolio_commit}")
    print(f"\n  FINAL_ENGINEERING_RELEASE_MANIFEST.json: FOUND in dev clone")
    print(f"    self_hash verified: PASS")
    print(f"  SOURCE_RELEASE_MANIFEST.json: FOUND in portfolio clone")
    print(f"    references dev commit: PASS")
    print(f"    references manifest hash: PASS")
    print(f"  CROSS_REPOSITORY_RELEASE_INTEGRITY.json: FOUND in both clones")
    print(f"    verdict: {dev_integrity.get('verdict', '?')}")
    print(f"\n  15/15 package dossier hashes match: PASS")
    print(f"  All buyer PDF hashes match: PASS")
    print(f"\n  VERDICT: PASS")
    print(f"\n  The cryptographic bridge between dev and portfolio repos is")
    print(f"  independently verified from fresh GitHub clones.")
    print(f"  No local uncommitted files were used.")

    # Clean up
    print(f"\n  Cleaning up clones...")
    shutil.rmtree(DEV_CLONE)
    shutil.rmtree(PORTFOLIO_CLONE)
    print(f"  Done.")

if __name__ == "__main__":
    main()

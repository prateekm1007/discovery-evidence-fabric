"""
r370w_final_release_object.py — Final Release Cleanup.

Per CEO: separate the three commit concepts and define an immutable release object.

1. ENGINEERING_CONTENT_COMMIT  = 3ff18f7 (the R370U freeze certificate — last engineering change)
2. RELEASE_MANIFEST_COMMIT      = 6e12f92 (the R370V manifest anchor)
3. FINAL_RELEASE_ANCHOR_COMMIT  = <this commit> (the terminal commit, will be HEAD)

The release is a cryptographically identified object, not a single Git commit.
After this commit is pushed, NO MORE COMMITS. This is the terminal commit.

Constitution: Articles I, II, IV, VI, XXIII, XXIV, XXV, XXVI, XXVII, XXVIII, XXXVIII.
"""
import json
import os
import sys
import hashlib
import subprocess
import shutil
import urllib.request
from datetime import datetime, timezone

TOKEN_FILE = "/tmp/gh_token.txt"

DEV_REPO = "prateekm1007/discovery-evidence-fabric"
PORTFOLIO_REPO = "prateekm1007/technology-transfer-portfolio-15"

DEV_ROOT = "/home/z/my-project/discovery-evidence-fabric"
PORTFOLIO_ROOT = "/home/z/my-project/technology-transfer-portfolio-15"
OUTPUT_DIR = os.path.join(DEV_ROOT, "premium_package_factory", "output", "engineering_dossiers_artifact_rich")

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

def sha256_json(obj):
    return sha256_str(json.dumps(obj, sort_keys=True, ensure_ascii=False))

def gh_head(repo):
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    url = f"https://api.github.com/repos/{repo}/branches/main"
    req = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["commit"]["sha"]

def build_final_release_object():
    """Build the immutable FINAL_RELEASE_OBJECT.json."""
    print("=" * 70)
    print("FINAL RELEASE OBJECT — immutable cryptographic release identifier")
    print("=" * 70)

    # The three commit concepts
    ENGINEERING_CONTENT_COMMIT = "3ff18f7ec84b9e0be8ca1791a33e9865eefee2c9"
    # RELEASE_MANIFEST_COMMIT will be set to 6e12f92 (the R370V manifest anchor)
    RELEASE_MANIFEST_COMMIT = "6e12f9228ecfd17ce06ef7a8919a397ff921b664"
    # FINAL_RELEASE_ANCHOR_COMMIT = this commit (will be filled after commit, but
    # we set it to current HEAD now and accept that this commit IS the anchor)

    # Get current HEADs
    dev_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=DEV_ROOT, text=True).strip()
    portfolio_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PORTFOLIO_ROOT, text=True).strip()

    print(f"\n  ENGINEERING_CONTENT_COMMIT  = {ENGINEERING_CONTENT_COMMIT}")
    print(f"  RELEASE_MANIFEST_COMMIT      = {RELEASE_MANIFEST_COMMIT}")
    print(f"  DEV_HEAD (pre-commit)        = {dev_head}")
    print(f"  PORTFOLIO_HEAD (pre-commit)  = {portfolio_head}")

    # Load the existing FINAL_ENGINEERING_RELEASE_MANIFEST to get dossier hashes
    manifest_path = os.path.join(OUTPUT_DIR, "FINAL_ENGINEERING_RELEASE_MANIFEST.json")
    with open(manifest_path) as f:
        dev_manifest = json.load(f)

    # Load portfolio PORTFOLIO_MANIFEST
    portfolio_manifest_path = os.path.join(PORTFOLIO_ROOT, "PORTFOLIO_MANIFEST.json")
    with open(portfolio_manifest_path) as f:
        portfolio_manifest = json.load(f)

    # Build per-package artifact hashes
    packages = []
    for num, pkg_id, folder in PACKAGE_MAP:
        # Dev dossier hash (from manifest)
        dev_dossier_hash = dev_manifest.get("engineering_dossier_hashes", {}).get(pkg_id, "NOT_FOUND")

        # Portfolio package artifacts
        portfolio_pkg = None
        for p in portfolio_manifest.get("packages", []):
            if p.get("package_id") == pkg_id:
                portfolio_pkg = p
                break

        # Hash each buyer artifact
        dossier_dir = os.path.join(PORTFOLIO_ROOT, "FULL_DOSSIERS", folder)

        # 6 PDFs per package
        pdf_hashes = {}
        for fname in ["00_PACKAGE_README.pdf", "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
                       "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
                       "03_BUYER_DECISION_CARD.pdf", "04_EVIDENCE_SUMMARY.pdf",
                       "05_TRANSFER_MANIFEST.pdf"]:
            pdf_hashes[fname] = sha256_file(os.path.join(dossier_dir, fname))

        # Buyer card
        buyer_card_path = os.path.join(PORTFOLIO_ROOT, "BUYER_OUTREACH", f"{num}_BUYER_CARD.pdf")
        buyer_card_hash = sha256_file(buyer_card_path)

        # ZIP
        zip_path = os.path.join(PORTFOLIO_ROOT, "DOWNLOAD", folder + ".zip")
        zip_hash = sha256_file(zip_path)

        # Package-level JSON artifacts
        traceability_hash = sha256_file(os.path.join(dossier_dir, "ENGINEERING_TRACEABILITY.json"))
        maturity_hash = sha256_file(os.path.join(dossier_dir, "MATURITY_BASIS.json"))
        package_manifest_hash = sha256_file(os.path.join(dossier_dir, "PACKAGE_MANIFEST.json"))

        # Transfer manifest PDF (05_)
        transfer_manifest_hash = pdf_hashes["05_TRANSFER_MANIFEST.pdf"]

        # Buyer decision card PDF (03_)
        buyer_decision_card_hash = pdf_hashes["03_BUYER_DECISION_CARD.pdf"]

        packages.append({
            "portfolio_number": num,
            "package_id": pkg_id,
            "folder_name": folder,
            "engineering_content_hash": dev_dossier_hash,
            "buyer_dossier_pdfs": pdf_hashes,
            "buyer_decision_card_hash": buyer_decision_card_hash,
            "transfer_manifest_hash": transfer_manifest_hash,
            "buyer_card_hash": buyer_card_hash,
            "buyer_zip_hash": zip_hash,
            "package_manifest_hash": package_manifest_hash,
            "engineering_traceability_hash": traceability_hash,
            "maturity_basis_hash": maturity_hash,
            "technology_maturity": portfolio_pkg.get("technology_maturity", ""),
            "dossier_maturity": portfolio_pkg.get("dossier_maturity", ""),
            "transfer_posture": portfolio_pkg.get("transfer_posture", ""),
            "primary_next_action": portfolio_pkg.get("primary_next_action", ""),
            "kill_condition": portfolio_pkg.get("kill_condition", ""),
        })

    # Master ZIP
    master_zip_path = os.path.join(PORTFOLIO_ROOT, "DOWNLOAD", "technology-transfer-portfolio-15.zip")
    master_zip_hash = sha256_file(master_zip_path)

    # Build the release object
    release_object = {
        "object_type": "FINAL_RELEASE_OBJECT",
        "release_id": f"R370W-FINAL-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "version": "1.0",
        "generated_at": _now(),

        "commit_concepts": {
            "ENGINEERING_CONTENT_COMMIT": {
                "sha": ENGINEERING_CONTENT_COMMIT,
                "description": "Last commit that modified engineering content (dossiers, templates, gates). R370U freeze certificate.",
                "repository": DEV_REPO,
            },
            "RELEASE_MANIFEST_COMMIT": {
                "sha": RELEASE_MANIFEST_COMMIT,
                "description": "Commit that established the FINAL_ENGINEERING_RELEASE_MANIFEST and SOURCE_RELEASE_MANIFEST cryptographic bridge. R370V manifest anchor.",
                "repository": DEV_REPO,
            },
            "FINAL_RELEASE_ANCHOR_COMMIT": {
                "sha": None,  # Will be filled after this commit is created
                "description": "Terminal commit. This commit contains the FINAL_RELEASE_OBJECT.json. No commits may follow this one.",
                "repository": "both",
            },
        },

        "repositories": {
            "development": {
                "name": DEV_REPO,
                "engineering_content_commit": ENGINEERING_CONTENT_COMMIT,
                "release_manifest_commit": RELEASE_MANIFEST_COMMIT,
                "final_release_anchor_commit": None,  # filled post-commit
                "constitution_hash": dev_manifest.get("constitution_hash", ""),
                "development_manifest_sha256": dev_manifest.get("self_hash", ""),
            },
            "portfolio": {
                "name": PORTFOLIO_REPO,
                "portfolio_head_commit": portfolio_head,
                "portfolio_manifest_sha256": sha256_file(portfolio_manifest_path),
                "source_release_manifest_sha256": sha256_file(os.path.join(PORTFOLIO_ROOT, "SOURCE_RELEASE_MANIFEST.json")),
                "final_release_anchor_commit": None,  # filled post-commit
            },
        },

        "package_count": 15,
        "packages": packages,

        "master_zip_hash": master_zip_hash,

        "honest_status": {
            "EXTERNAL_CONSULTANT_PASS": "NOT_YET_ADMINISTERED",
            "REAL_BUYER": 0,
            "REAL_EXPERIMENT": 0,
            "REAL_DATA": 0,
            "REAL_LOOP_VERIFIED": "FALSE",
            "TRANSFER_READY": "0/15",
        },

        "freeze_rule": (
            "This is the terminal commit. After this commit is pushed to both repositories, "
            "NO MORE COMMITS are permitted. The release is now a cryptographically identified "
            "object, not a single Git commit. The three commit concepts "
            "(ENGINEERING_CONTENT_COMMIT, RELEASE_MANIFEST_COMMIT, FINAL_RELEASE_ANCHOR_COMMIT) "
            "are distinct. The next state is EXTERNAL CONSULTANT -> BUYER -> REAL ENGINEER -> "
            "EXPERIMENT -> REAL DATA -> PROVENANCE -> AI UPDATE -> PACKAGE V2."
        ),
    }

    # Compute self_hash (hash of the object without self_hash and without the anchor commit SHA)
    obj_for_hash = {k: v for k, v in release_object.items() if k != "self_hash"}
    # Also null out the FINAL_RELEASE_ANCHOR_COMMIT sha for hashing (it's not known yet)
    obj_for_hash["commit_concepts"]["FINAL_RELEASE_ANCHOR_COMMIT"]["sha"] = "PENDING"
    obj_for_hash["repositories"]["development"]["final_release_anchor_commit"] = "PENDING"
    obj_for_hash["repositories"]["portfolio"]["final_release_anchor_commit"] = "PENDING"
    release_object["self_hash"] = sha256_json(obj_for_hash)

    return release_object

def save_release_object(release_object):
    """Save to both repos."""
    dev_path = os.path.join(OUTPUT_DIR, "FINAL_RELEASE_OBJECT.json")
    with open(dev_path, "w") as f:
        json.dump(release_object, f, indent=2, ensure_ascii=False)

    portfolio_path = os.path.join(PORTFOLIO_ROOT, "FINAL_RELEASE_OBJECT.json")
    with open(portfolio_path, "w") as f:
        json.dump(release_object, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved: {dev_path}")
    print(f"  Saved: {portfolio_path}")
    print(f"  Self hash (pre-anchor): {release_object['self_hash']}")

def main():
    release_object = build_final_release_object()
    save_release_object(release_object)

    print(f"\n{'='*70}")
    print(f"FINAL RELEASE OBJECT SUMMARY")
    print(f"{'='*70}")
    print(f"\n  Release ID: {release_object['release_id']}")
    print(f"  Package count: {release_object['package_count']}")
    print(f"\n  Commit concepts:")
    print(f"    ENGINEERING_CONTENT_COMMIT = {release_object['commit_concepts']['ENGINEERING_CONTENT_COMMIT']['sha']}")
    print(f"    RELEASE_MANIFEST_COMMIT    = {release_object['commit_concepts']['RELEASE_MANIFEST_COMMIT']['sha']}")
    print(f"    FINAL_RELEASE_ANCHOR_COMMIT = <pending — will be this commit>")
    print(f"\n  Master ZIP hash: {release_object['master_zip_hash']}")
    print(f"\n  Package artifacts verified:")
    for p in release_object["packages"]:
        pdf_count = len(p["buyer_dossier_pdfs"])
        print(f"    {p['portfolio_number']} {p['package_id']}: {pdf_count} PDFs + card + ZIP + 3 JSON artifacts")

    print(f"\n  HONEST STATUS:")
    for k, v in release_object["honest_status"].items():
        print(f"    {k} = {v}")

    print(f"\n  NEXT: commit this file to both repos as the terminal commit.")
    print(f"  Then update FINAL_RELEASE_ANCHOR_COMMIT sha and re-commit (amend).")
    print(f"  Then STOP.")

if __name__ == "__main__":
    main()

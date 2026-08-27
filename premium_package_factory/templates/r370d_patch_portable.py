"""
r370d_patch_portable.py — Patch all R370B/R370C scripts to use portable repo-root discovery.

Replaces hard-coded:
    REPO_ROOT = "/home/z/my-project/discovery-evidence-fabric"
    SCRIPTS_DIR = "/home/z/my-project/scripts"
    sys.path.insert(0, "/home/z/my-project/scripts")

With portable:
    from gates.r370_portable import find_repo_root, get_output_dir, setup_python_path
    REPO_ROOT = find_repo_root()
    setup_python_path()

Constitution: Article XXIII (never infer repository state from local state),
Article XXVI (no self-certification — independent reproduction required).
"""

import os
import re
import sys

REPO_ROOT = "/home/z/my-project/discovery-evidence-fabric"

# Files to patch (relative to repo root)
FILES_TO_PATCH = [
    "premium_package_factory/gates/r370c_adversarial_qa.py",
    "premium_package_factory/gates/r370c_number_register.py",
    "premium_package_factory/gates/r370c_save_standard_register.py",
    "premium_package_factory/gates/r370c_technical_factuality_gate.py",
    "premium_package_factory/templates/r370c_factual_fix.py",
    "premium_package_factory/templates/r370c_factual_fix_2.py",
    "premium_package_factory/templates/r370c_factual_fix_3.py",
    "premium_package_factory/gates/r370b_adversarial_qa.py",
    "premium_package_factory/gates/r370b_leakage_detector.py",
    "premium_package_factory/gates/r370b_qa_gate.py",
    "premium_package_factory/templates/r370b_fix_exemplars.py",
    "premium_package_factory/templates/r370b_fix_leakage.py",
    "premium_package_factory/templates/r370b_generator.py",
]


def patch_file(filepath):
    """Patch a single file to use portable repo-root discovery."""
    with open(filepath) as f:
        content = f.read()

    original = content
    changes = []

    # Determine if file is in gates/ or templates/ to compute the relative import path
    if "/gates/" in filepath:
        portable_import = "from gates.r370_portable import find_repo_root, get_output_dir, get_external_evidence_dir, setup_python_path"
    else:
        portable_import = "from gates.r370_portable import find_repo_root, get_output_dir, get_external_evidence_dir, setup_python_path"

    # Pattern 1: Replace REPO_ROOT = "/home/z/my-project/discovery-evidence-fabric"
    pattern1 = r'REPO_ROOT\s*=\s*"/home/z/my-project/discovery-evidence-fabric"'
    if re.search(pattern1, content):
        content = re.sub(pattern1, 'REPO_ROOT = find_repo_root()', content)
        changes.append("REPO_ROOT hardcoded → find_repo_root()")

    # Pattern 2: Replace SCRIPTS_DIR = "/home/z/my-project/scripts"
    pattern2 = r'SCRIPTS_DIR\s*=\s*"/home/z/my-project/scripts"'
    if re.search(pattern2, content):
        content = re.sub(pattern2, 'SCRIPTS_DIR = None  # use setup_python_path() instead', content)
        changes.append("SCRIPTS_DIR hardcoded → None (use setup_python_path)")

    # Pattern 3: Replace sys.path.insert(0, "/home/z/my-project/scripts")
    pattern3 = r'sys\.path\.insert\(0,\s*"/home/z/my-project/scripts"\)'
    if re.search(pattern3, content):
        content = re.sub(pattern3, 'setup_python_path()  # portable: adds gates/ and templates/ to sys.path', content)
        changes.append("sys.path hardcoded → setup_python_path()")

    # Pattern 4: Replace OUTPUT_DIR = "/home/z/my-project/discovery-evidence-fabric/premium_package_factory/output/engineering_dossiers_artifact_rich"
    pattern4 = r'OUTPUT_DIR\s*=\s*"/home/z/my-project/discovery-evidence-fabric/premium_package_factory/output/engineering_dossiers_artifact_rich"'
    if re.search(pattern4, content):
        content = re.sub(pattern4, 'OUTPUT_DIR = get_output_dir()', content)
        changes.append("OUTPUT_DIR hardcoded → get_output_dir()")

    # Pattern 5: Replace EXTERNAL_EVIDENCE_DIR = os.path.join(REPO_ROOT, "external_evidence")
    # This is already portable if REPO_ROOT is portable, so no change needed

    # Add the portable import if we made any changes and it's not already there
    if content != original and "r370_portable" not in content:
        # Insert import after the existing imports
        # Find the last "import" or "from" line in the header
        lines = content.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines[:30]):
            if line.startswith("import ") or line.startswith("from "):
                insert_idx = i + 1
            # Also insert after sys.path lines
            if "sys.path" in line:
                insert_idx = i + 1

        # Insert the portable import
        lines.insert(insert_idx, portable_import)
        content = "\n".join(lines)
        changes.append(f"Added import: {portable_import}")

    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        return changes
    return []


def main():
    print("=" * 70)
    print("R370D PATCH: Replace hardcoded paths with portable repo-root discovery")
    print("=" * 70)

    total_patched = 0
    for rel_path in FILES_TO_PATCH:
        filepath = os.path.join(REPO_ROOT, rel_path)
        if not os.path.exists(filepath):
            print(f"  SKIP (not found): {rel_path}")
            continue
        changes = patch_file(filepath)
        if changes:
            print(f"  PATCHED: {rel_path}")
            for ch in changes:
                print(f"    - {ch}")
            total_patched += 1
        else:
            print(f"  NO CHANGE: {rel_path}")

    print(f"\nTotal files patched: {total_patched}/{len(FILES_TO_PATCH)}")

    # Verify no hardcoded paths remain
    print("\nVerifying no hardcoded paths remain...")
    remaining = []
    for rel_path in FILES_TO_PATCH:
        filepath = os.path.join(REPO_ROOT, rel_path)
        if not os.path.exists(filepath):
            continue
        with open(filepath) as f:
            content = f.read()
        if "/home/z/my-project" in content:
            # Find the offending lines
            for i, line in enumerate(content.split("\n"), 1):
                if "/home/z/my-project" in line and not line.strip().startswith("#"):
                    remaining.append(f"{rel_path}:{i}: {line.strip()}")
    if remaining:
        print(f"  WARNING: {len(remaining)} hardcoded paths remain:")
        for r in remaining[:10]:
            print(f"    {r}")
    else:
        print("  PASS: no hardcoded paths remain in any R370B/R370C script")


if __name__ == "__main__":
    main()

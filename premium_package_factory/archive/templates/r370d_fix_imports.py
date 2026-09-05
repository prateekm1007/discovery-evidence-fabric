"""
r370d_fix_imports.py — Fix the import paths in patched R370B/R370C scripts.

The previous patch used 'from gates.r370_portable import ...' which only works
when premium_package_factory/ is on sys.path. This script makes the import
robust by trying multiple import strategies.
"""

import os
import re

REPO_ROOT = "/home/z/my-project/discovery-evidence-fabric"

FILES_TO_FIX = [
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

# Robust import block that tries multiple strategies
ROBUST_IMPORT_BLOCK = '''# Portable repo-root discovery (R370D: replaces hardcoded paths)
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
'''


def fix_file(filepath):
    """Fix the import in a single file."""
    with open(filepath) as f:
        content = f.read()

    # Find the existing portable import line
    patterns = [
        r'from gates\.r370_portable import find_repo_root, get_output_dir, get_external_evidence_dir, setup_python_path\nREPO_ROOT = find_repo_root\(\)\n',
        r'from gates\.r370_portable import find_repo_root, get_output_dir, get_external_evidence_dir, setup_python_path\n',
    ]

    matched = False
    for pat in patterns:
        if re.search(pat, content):
            # Replace the first occurrence with the robust block
            content = re.sub(pat, ROBUST_IMPORT_BLOCK, content, count=1)
            matched = True
            break

    if not matched:
        return False

    # Also remove any duplicate REPO_ROOT = find_repo_root() that might exist after the block
    # (the robust block already sets REPO_ROOT)
    # Find lines after the block that set REPO_ROOT
    lines = content.split("\n")
    in_block = False
    block_end = -1
    for i, line in enumerate(lines):
        if "# Portable repo-root discovery" in line:
            in_block = True
        if in_block and line.strip() == "REPO_ROOT = find_repo_root()":
            block_end = i
            in_block = False
        elif block_end >= 0 and line.strip() == "REPO_ROOT = find_repo_root()":
            # This is a duplicate — remove it
            lines[i] = None  # mark for removal

    # Remove None lines
    lines = [l for l in lines if l is not None]
    content = "\n".join(lines)

    with open(filepath, "w") as f:
        f.write(content)
    return True


def main():
    print("Fixing import paths for portability...")
    fixed = 0
    for rel_path in FILES_TO_FIX:
        filepath = os.path.join(REPO_ROOT, rel_path)
        if not os.path.exists(filepath):
            continue
        if fix_file(filepath):
            print(f"  FIXED: {rel_path}")
            fixed += 1
        else:
            print(f"  NO CHANGE: {rel_path}")
    print(f"\nTotal: {fixed}/{len(FILES_TO_FIX)} files fixed")


if __name__ == "__main__":
    main()

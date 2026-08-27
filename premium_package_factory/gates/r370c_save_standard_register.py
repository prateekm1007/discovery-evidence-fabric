"""
r370c_save_standard_register.py — Save engineering standard register to JSON.
"""

import json
import os
import sys

setup_python_path()  # portable: adds gates/ and templates/ to sys.path
from r370c_standard_register import STANDARD_REGISTER
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


OUTPUT_DIR = get_output_dir()


def main():
    register = {
        "register_type": "Engineering Standard Register",
        "version": "R370C-1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "constitution_compliance": "Article II (exact evidence beats semantic plausibility), Article VI (no fabricated provenance), Article XXVII (threshold provenance)",
        "total_standards_registered": len(STANDARD_REGISTER),
        "verified_standards_count": sum(1 for v in STANDARD_REGISTER.values() if "r370b_error" not in v),
        "known_errors_count": sum(1 for v in STANDARD_REGISTER.values() if "r370b_error" in v),
        "standards": STANDARD_REGISTER
    }
    register_path = os.path.join(OUTPUT_DIR, "ENGINEERING_STANDARD_REGISTER.json")
    with open(register_path, "w") as f:
        json.dump(register, f, indent=2, ensure_ascii=False)
    print(f"Engineering Standard Register saved: {register_path}")
    print(f"Total standards registered: {len(STANDARD_REGISTER)}")
    print(f"Verified (current) standards: {register['verified_standards_count']}")
    print(f"Known errors (R370B wrong citations): {register['known_errors_count']}")
    print()
    print("Known errors:")
    for k, v in STANDARD_REGISTER.items():
        if "r370b_error" in v:
            print(f"  {k}: {v['title'][:80]}")
            print(f"    ERROR: {v['r370b_error'][:120]}")


if __name__ == "__main__":
    main()

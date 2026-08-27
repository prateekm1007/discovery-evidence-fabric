"""
r370c_save_standard_register.py — Save engineering standard register to JSON.
"""

import json
import os
import sys

sys.path.insert(0, "/home/z/my-project/scripts")
from r370c_standard_register import STANDARD_REGISTER
from datetime import datetime, timezone

OUTPUT_DIR = "/home/z/my-project/discovery-evidence-fabric/premium_package_factory/output/engineering_dossiers_artifact_rich"


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

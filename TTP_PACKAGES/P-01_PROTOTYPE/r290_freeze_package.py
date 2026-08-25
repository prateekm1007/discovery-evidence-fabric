#!/usr/bin/env python3
"""
R290 P0 — Package Freeze: Hash-Pin Everything
==============================================

Per CEO R290 P0: "Freeze controller version, rate limit, sensor-health
behavior, attack definitions, B comparator, acceptance criteria, data schema.
Everything must be hash-pinned."

This script computes SHA-256 hashes of all frozen P-01 artifacts and
creates a canonical freeze manifest. The manifest is the "configuration
control" record — any change to any file invalidates the freeze.

This implements NASA Systems Engineering Handbook configuration management
and FDA design control requirements.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(HERE, "..", "..")

FROZEN_FILES = {
    # Controller code
    "controller_V2": "TTP_PACKAGES/P-01_PROTOTYPE/10_V2_comparison.py",
    "controller_V2_full": "TTP_PACKAGES/P-01_PROTOTYPE/12_V2_full_validation.py",
    "controller_V2_1": "TTP_PACKAGES/P-01_PROTOTYPE/14_V2_1_validation.py",
    
    # Frozen mechanism
    "frozen_mechanism": "TTP_PACKAGES/P-01_PROTOTYPE/FROZEN_MECHANISM_R287.md",
    "frozen_commercial_mechanism": "TTP_PACKAGES/P-01_PROTOTYPE/FROZEN_COMMERCIAL_MECHANISM_R289.json",
    
    # Pre-registrations
    "preregistration_R282": "TTP_PACKAGES/P-01_PROTOTYPE/PRE_REGISTERED_SUCCESS_CRITERION_R282.json",
    "preregistration_V2_1": "TTP_PACKAGES/P-01_PROTOTYPE/V2_1_PRE_REGISTRATION.json",
    
    # Provenance
    "provenance_manifest": "TTP_PACKAGES/P-01_PROTOTYPE/DATASET_PROVENANCE_MANIFEST.json",
    
    # Canonical datasets
    "canonical_180run": "TTP_PACKAGES/P-01_PROTOTYPE/p01_R285_CANONICAL_decisive_comparison.json",
    "ablation_225run": "TTP_PACKAGES/P-01_PROTOTYPE/p01_R282_ablation_5seeds.json",
    
    # Prior art
    "prior_art_landscape": "TTP_PACKAGES/P-01_PROTOTYPE/PRIOR_ART_LANDSCAPE_R287.json",
    
    # Physical bench
    "bench_protocol_R284": "TTP_PACKAGES/P-01_PROTOTYPE/PHYSICAL_BENCH_PROTOCOL_R284_COMMERCIAL.json",
    "bench_package_R283": "TTP_PACKAGES/P-01_PROTOTYPE/PHYSICAL_BENCH_COMPLETE_PACKAGE_R283.json",
    "prototype_BOM": "TTP_PACKAGES/P-01_PROTOTYPE/PROTOTYPE_BOM_R289_BUILDABLE.json",
    
    # Commercial TTP
    "commercial_TTP": "TTP_PACKAGES/P-01_PROTOTYPE/COMMERCIAL_TTP_R289.md",
    
    # Buyer outreach
    "buyer_package_R286": "TTP_PACKAGES/COMMERCIAL_LOOP/BUYER_OUTREACH_PACKAGE_R286.json",
    "five_buyers": "TTP_PACKAGES/COMMERCIAL_LOOP/FIVE_SPECIFIC_TECHNICAL_BUYERS.json",
}

def compute_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def main():
    freeze_manifest = {
        "freeze_id": "P-01-FREEZE-R290",
        "freeze_timestamp": datetime.now(timezone.utc).isoformat(),
        "freeze_reason": "Per CEO R290 P0: hash-pin all frozen artifacts. Implements NASA SE configuration management + FDA design control.",
        "frozen_parameters": {
            "rate_limit_max_per_sec": 0.02,
            "alpha_min": 0.05,
            "drainage_floor_fraction": 0.50,
            "hysteresis_deadband": 0.03,
            "sensor_health_threshold_mmhg": 0.5,
            "sensor_health_recovery_consecutive": 3,
            "P_MIN_MMHG": 5.0,
            "P_MAX_MMHG": 20.0,
            "P_TARGET_MMHG": 12.0,
            "F_MAX_PER_SEG": 0.30,
            "Q_PRODUCTION_ML_MIN": 0.30,
            "G_HEALTHY": 0.060,
            "DT_SEC": 1.0,
            "N_STEPS": 86400,
            "K_OCCL_DEFAULT": "1.0/3600.0",
            "SEEDS": [42, 43, 44, 45, 46],
            "ATTACK_MODES": [
                "none", "noise_3x", "sensor_dropout", "fast_occlusion",
                "slow_occlusion", "wrong_model", "multi_failure",
                "actuator_saturation", "controller_delay"
            ],
            "B_COMPARATOR": "V1.2 Arm D logic (predictive closed-loop, no rate limiting)",
            "V2_1_CONTROLLER": "V2 + sensor-health detector + safe fallback",
        },
        "acceptance_criteria": {
            "primary_endpoint": "time_to_critical_failure under noise_3x",
            "primary_threshold": "V2.1/B >= 2.0x AND V2.1 wins >= 4/5 seeds",
            "bench_falsification": "±30% tolerance. If bench differs >30%, simulator is WRONG.",
            "multi_failure_boundary": "Known catastrophic (peak 69.8 mmHg). Disclosed, not hidden."
        },
        "frozen_files": {},
        "freeze_rule": "Any change to any frozen file or parameter invalidates this freeze. A new freeze (P-01-FREEZE-R291) must be created with documented rationale. This implements NASA configuration control.",
    }
    
    print("=" * 100)
    print("P-01 PACKAGE FREEZE — R290")
    print("Hash-pinning all frozen artifacts per CEO R290 P0")
    print("Implements: NASA SE configuration management + FDA design control")
    print("=" * 100)
    
    all_ok = True
    for name, rel_path in FROZEN_FILES.items():
        full_path = os.path.join(REPO_ROOT, rel_path)
        if os.path.exists(full_path):
            file_hash = compute_hash(full_path)
            file_size = os.path.getsize(full_path)
            freeze_manifest["frozen_files"][name] = {
                "path": rel_path,
                "sha256": file_hash,
                "size_bytes": file_size,
                "frozen_at": freeze_manifest["freeze_timestamp"],
            }
            print(f"  ✅ {name:35s} {file_hash[:16]}... ({file_size:>6} bytes)")
        else:
            freeze_manifest["frozen_files"][name] = {
                "path": rel_path,
                "sha256": "FILE_NOT_FOUND",
                "error": "File does not exist"
            }
            print(f"  ❌ {name:35s} FILE NOT FOUND: {rel_path}")
            all_ok = False
    
    # Save manifest
    manifest_path = os.path.join(HERE, "PACKAGE_FREEZE_MANIFEST_R290.json")
    with open(manifest_path, 'w') as f:
        json.dump(freeze_manifest, f, indent=2)
    
    print(f"\n{'='*100}")
    print(f"FREEZE {'COMPLETE' if all_ok else 'INCOMPLETE'}")
    print(f"Files frozen: {len(freeze_manifest['frozen_files'])}")
    print(f"Parameters frozen: {len(freeze_manifest['frozen_parameters'])}")
    print(f"Manifest: {manifest_path}")
    print(f"{'='*100}")
    
    if all_ok:
        print("\nAll P-01 artifacts are now hash-pinned and configuration-controlled.")
        print("Any change to any file invalidates this freeze.")
        print("This is the transition from simulation to technology transfer.")

if __name__ == "__main__":
    main()

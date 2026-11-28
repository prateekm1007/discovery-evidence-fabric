#!/usr/bin/env python3
"""scripts/r55_battery_migration_manifest.py — the machine-battery
migration manifest (claim c-0075; AM50 direction 3). Maps every
retired/scanner-era prose mechanism to its machine-path successor and
the CI test that pins the successor, and types which retirements are
executable now vs P2-gated (the v7.7 ablation baseline imports the
scanner layer; Art. 16 same-change accounting schedules its deletion
with the v7.7 retirement). Zero LLM, zero network."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "scripts" / "r55_battery_migration_manifest.json"

MANIFEST = {
    "record": "R55_BATTERY_MIGRATION_MANIFEST/1.0.0",
    "claim": "c-0075",
    "basis": "AM50 direction 3: 'delete the retired prose scanners "
             "(F57/F58/F59) per Art. 16 now that schema enums + "
             "computed physics carry the checks — machine-battery "
             "migration first'. This manifest IS the migration "
             "accounting: mechanism -> successor -> CI pin.",
    "migrations": [
        {"mechanism": "free-prose span extraction (the v7.7 "
                      "_MEASUREMENT/_QTY_COMPOUND/_QTY_OBJECT/_DERIVED "
                      "span hunt + the r26 _added_spans extraction)",
         "finding": "F57 (P/R 1.0 labelled structured extraction; "
                    "free-prose retired at engine level R43)",
         "successor": "candidate_schema 1.1.0 enum-typed fields + the "
                      "integrated engine route (no prose parsing in "
                      "the measured path)",
         "ci_pin": "tests/test_v8_generation_binds.py (23 tests) + "
                   "tests/r52_labelled_regression CI step (0/0/0)"},
        {"mechanism": "hard class declaration counted-inferred from "
                      "prose",
         "finding": "F58 CLOSED (schema enums)",
         "successor": "candidate_schema 1.1.0 wrap-only enums",
         "ci_pin": "tests/test_v8_generation_binds.py"},
        {"mechanism": "allowed-measures class bind (the AM29 D1 "
                      "constraint-class check)",
         "finding": "AM29 recurring closure",
         "successor": "population_search.declared_domain_classes (the "
                      "engine clamp)",
         "ci_pin": "the P1.4 regression leg A (0 allowed-measures "
                   "violations, CI-gated) + tests/test_r30_am29_binds "
                   "still pinning the v7.7-arm implementation"},
        {"mechanism": "physics direction from prose lexicon",
         "finding": "F59-adjacent; superseded by sign-of-result",
         "successor": "physics_checks: 12 relations, pint unit-checked, "
                      "deterministic classify_failure router (F66 "
                      "disambiguation rule R55)",
         "ci_pin": "tests/test_physics_checks.py + "
                   "tests/test_physics_checks_r54.py + the P1 "
                   "unit-checked measurement CI step (bar 0.80)"},
        {"mechanism": "per-branch live-token byte-grep driver "
                      "(scripts/r44_f59_scan.py)",
         "finding": "F59 precision lesson",
         "successor": "scripts/r45_all_refs_secret_scan.py (tips gate "
                      "+ git-mode + vault-value exact check)",
         "ci_pin": "tests/test_all_refs_secret_scan.py (14 tests) + "
                   "the CI tips-gate step; DELETED in R55 (zero "
                   "importers verified; ledger entry 4)"},
    ],
    "p2_gated_retirements": {
        "set": ["r24_constraint_scan", "r26_catalog_scan",
                "r27_standard_bill_scan", "r29_conversion_scan",
                "r29_operational_loss_scan", "r30_allowed_class_scan",
                "r30_physics_direction_scan"],
        "reason": "the v7.7 ablation baseline (scripts/r40_machine_v77.py) "
                  "imports the entire layer at runtime — verified "
                  "24-module import closure; the P2 matched-budget "
                  "ablation needs the baseline arm executable",
        "deletion_moment": "the same change that retires the v7.7 path "
                           "after the P2 ablation completes (Art. 16 "
                           "same-change accounting)",
    },
    "pre_existing_era_debt_observed": [
        "scripts/r16_a1w_generate imports missing r11_a1t_r1; "
        "scripts/r510_space_deploy + r456_space_deploy import missing "
        "r447_deploy_upload/r447_hf_deploy/r491_space_deploy — era "
        "one-shot drivers left import-broken by earlier rounds "
        "(pre-existing, outside R55 census; not deleted here — Art. 14 "
        "red-gate discipline: no deletion beyond the verified census)",
    ],
    "verdict": "MIGRATION ACCOUNTED — the machine battery carries every "
               "scanner-era check; one physically-retired scanner "
               "(r44_f59_scan, zero breakage); the r24-r30 layer "
               "P2-gated with the ledger entry recorded",
}


def main() -> None:
    OUT.write_text(json.dumps(MANIFEST, indent=1))
    print(json.dumps({"out": str(OUT.relative_to(REPO)),
                      "migrations": len(MANIFEST["migrations"]),
                      "p2_gated": len(
                          MANIFEST["p2_gated_retirements"]["set"])},
                     indent=1))


if __name__ == "__main__":
    main()

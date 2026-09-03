#!/usr/bin/env python3
"""R403 — generate tests/r403_corpus_pins.json: the sha256 pins for the
frozen-corpus files on the audit's section-15 immutable list (engine side).

The pins are COMPUTED from the current committed files (never hand-typed —
that is how citation drift gets manufactured). The consistency test then
asserts the files stay byte-identical forever after.

Run from the repo root: python3 scripts/r403_pin_hashes.py
"""
import hashlib
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CORPUS = REPO / "BENCHMARK_ENGINEERING_DOSSIERS" / "frozen_corpus_r370"
OUT = REPO / "tests" / "r403_corpus_pins.json"

IMMUTABLE = {
    "04_drainage_floor": ["MATURITY_BASIS.json", "PACKAGE_MANIFEST.json",
                          "PACKAGE_MUTATION_CERTIFICATE_P-07_V2.json",
                          "V2_MUTATION_ADDENDUM.json"],
    "08_nir_photovoltaic": ["MATURITY_BASIS.json", "PACKAGE_MANIFEST.json"],
    "11_gravity_damper": ["MATURITY_BASIS.json", "PACKAGE_MANIFEST.json"],
    "13_pressure_sensor": ["MATURITY_BASIS.json", "PACKAGE_MANIFEST.json",
                           "PACKAGE_MUTATION_CERTIFICATE_P-27-R1_V2.json",
                           "V2_MUTATION_ADDENDUM.json"],
    "14_acoustic_detection": ["MATURITY_BASIS.json", "PACKAGE_MANIFEST.json",
                              "PACKAGE_MUTATION_CERTIFICATE_P-28_V2.json",
                              "V2_MUTATION_ADDENDUM.json"],
}


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def main():
    # Guard: the worktree copy must equal the committed blob (pins must pin
    # COMMITTED bytes, not local edits).
    dirty = []
    for folder, names in IMMUTABLE.items():
        for n in names:
            rel = f"BENCHMARK_ENGINEERING_DOSSIERS/frozen_corpus_r370/{folder}/{n}"
            blob = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{rel}"],
                                  capture_output=True).stdout
            disk = (REPO / rel).read_bytes()
            if blob != disk:
                dirty.append(rel)
    if dirty:
        print("REFUSING: worktree differs from HEAD for:", dirty)
        return 1

    pins = {}
    for folder, names in IMMUTABLE.items():
        for n in names:
            p = CORPUS / folder / n
            pins[f"{folder}/{n}"] = hashlib.sha256(p.read_bytes()).hexdigest()

    OUT.write_text(json.dumps(pins, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(pins)} pins to {OUT}")
    for k, v in sorted(pins.items()):
        print(f"  {k}  {v[:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())

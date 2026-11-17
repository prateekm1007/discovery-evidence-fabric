#!/usr/bin/env python3
"""Article 22 measured-path gate (epistemic constitution v3.2.0 CI
addition for F61; ratification claim c-0080).

CLAUSE UNDER ENFORCEMENT (Art. 22, v3.2.0): "MEASURED-PATH declaration:
every measurement/holdout driver is manifested
(eval/measured_path_manifest.json) naming the discovery_fabric/engine
modules it imports; the CI import check flags a wrapper-only
measurement — a driver whose measured path never enters the engine."

GROUND TRUTH (F61): the holdouts measured a 559-line wrapper, not the
3716-line engine. The manifest + AST import check makes the bypass
structurally visible: a measurement entry whose driver never imports a
declared engine module REDS the gate, and a driver that IMPORTS engine
modules it does not declare REDS the gate (the declaration must match
the measured reality, both directions).
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "eval" / "measured_path_manifest.json"


def _imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_manifest_covers_the_active_measurement_drivers():
    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert d["record"].startswith("R59_MEASURED_PATH_MANIFEST")
    entries = d["entries"]
    assert len(entries) >= 4, (
        "the manifest must cover the P1 legs, the P2 ablation, and the "
        "determinism probe at minimum")
    drivers = {e["driver"] for e in entries}
    for must in ("scripts/r52_labelled_regression.py",
                 "scripts/r54_p1_unit_checked_measurement.py",
                 "scripts/r58_p2_ablation_driver.py"):
        assert must in drivers, (
            f"the active measurement driver {must} is NOT manifested "
            "(an unmanifested measurement is the F61 blind spot)")


def test_every_manifested_driver_really_imports_its_declared_modules():
    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    offenders = []
    for e in d["entries"]:
        driver = REPO / e["driver"]
        assert driver.exists(), (
            f"manifested driver missing: {e['driver']}")
        imported = _imports_of(driver)
        for mod in e["engine_imports"]:
            # direct import OR any import whose module path starts
            # with the declared package prefix
            hit = any(m == mod or m.startswith(mod + ".")
                      or mod.startswith(m + ".") for m in imported)
            if not hit:
                offenders.append((e["driver"], mod, sorted(imported)[:6]))
    assert not offenders, (
        "MEASURED-PATH DECLARATION MISMATCH (the F61 wrapper-only "
        f"pattern): declared engine module not imported — {offenders}")


def test_declared_imports_do_not_overstate_the_engine_surface():
    # reverse direction: a driver declaring MORE engine surface than
    # it imports is an untruthful declaration (the manifest is the
    # measured-path ledger, not aspiration).
    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    offenders = []
    for e in d["entries"]:
        imported = _imports_of(REPO / e["driver"])
        engine_imported = {m for m in imported
                           if m.startswith("discovery_fabric")}
        declared = set(e["engine_imports"])
        undeclared = {m for m in engine_imported
                      if not any(m == dm or m.startswith(dm + ".")
                                 or dm.startswith(m + ".")
                                 for dm in declared)}
        if undeclared:
            offenders.append((e["driver"], sorted(undeclared)))
    assert not offenders, (
        f"UNDECLARED ENGINE IMPORTS in a manifested measurement "
        f"driver: {offenders}")


def test_ledgers_named_by_the_manifest_exist():
    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing = []
    for e in d["entries"]:
        ledger = REPO / e["ledger"]
        # the ablation criteria file materializes at the one-shot run;
        # its ABSENCE before the run is typed, not a missing declaration
        if not ledger.exists() and \
                e["work_id"] == "r58-p2-dev-ablation-machine-leg":
            continue
        if not ledger.exists():
            missing.append(e["ledger"])
    assert not missing, (
        f"manifested ledger artifacts missing (the run ledger is part "
        f"of the measured-path declaration): {missing}")


def test_the_engine_is_not_a_wrapper_facade():
    # the manifest's engine modules must BE the engine: the declared
    # modules must exist under discovery_fabric/engine/ (a wrapper
    # could declare a shim path that never reaches the 3716-line
    # engine — the manifest check pins the real module files).
    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for e in d["entries"]:
        for mod in e["engine_imports"]:
            parts = mod.split(".")
            assert parts[:2] == ["discovery_fabric", "engine"], (
                f"a manifest entry declares a non-engine module: {mod}")
            mod_file = REPO / "discovery_fabric" / "engine" / \
                (parts[2] + ".py")
            assert mod_file.exists(), (
                f"declared engine module file missing: {mod_file}")

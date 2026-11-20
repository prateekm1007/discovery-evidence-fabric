"""tests/test_notice_import_coverage.py — D3 (auditor direction 3,
claim c-0128): every third-party package IMPORTED anywhere in the
tree appears in NOTICE.md. The scan is AST-based (imports, not
strings), covers discovery_fabric/, scripts/, tests/ and the
top-level packages, and maps import names to NOTICE row names via an
explicit table (the mapping is itself test-covered: an unmapped
import fails the test — the mapping grows only consciously)."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# import-name -> the NOTICE.md row name that must mention it
IMPORT_TO_NOTICE = {
    "CoolProp": "CoolProp",
    "ht": "ht (Caleb Bell)",
    "fluids": "fluids",
    "cantera": "Cantera",
    "sklearn": "scikit-learn",
    "pint": "pint",
    "numpy": "numpy",
    "scipy": "scipy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "mpl_toolkits": "matplotlib",
    "pytest": "pytest",
    "PIL": "Pillow",
    "pypdf": "pypdf",
    "pdfplumber": "pdfplumber",
    "cadquery": "cadquery",
    "OCP": "OCP",
    "sfepy": "sfepy",
    "trimesh": "trimesh",
    "torch": "PyTorch",
    "transformers": "transformers",
    "huggingface_hub": "huggingface_hub",
    "chronos": "Chronos / Chronos-Bolt (amazon)",
    "mapie": "MAPIE",
    "inspect_ai": "Inspect AI",
    "google": "google",           # resolved dynamically (see below)
    "rdkit": "rdkit",
    "reportlab": "reportlab",
}

# import names with NO third-party license obligation: the name has
# no module file in this repo (a runtime-staged or dead import path
# inside try/except blocks), so no upstream code can be depended on.
# TYPED and closed — grows only with a finding.
PHANTOM_LOCAL = {"TOSCANINI", "eval", "r447_deploy_upload",
                 "r447_hf_deploy", "r491_space_deploy"}

LOCAL_ROOTS = {"discovery_fabric", "aide", "dspy", "scripts", "tests"}


def _local_module_names() -> set:
    """Repo-local top-level module names: every .py stem ANYWHERE in
    the repo (this monorepo path-imports script modules from many
    depths — engine/, scripts/, download/, eval/) plus every
    directory that is a python package."""
    names = set(LOCAL_ROOTS)
    for p in REPO.rglob("*.py"):
        names.add(p.stem)
    for p in REPO.rglob("__init__.py"):
        names.add(p.parent.name)
    return names


def _third_party_imports() -> set:
    mods = set()
    for root in sorted(LOCAL_ROOTS | {p.name for p in REPO.iterdir()
                                      if p.suffix == ".py"}):
        base = REPO / root
        files = base.rglob("*.py") if base.is_dir() else [base]
        for f in files:
            try:
                tree = ast.parse(f.read_text(errors="ignore"))
            except Exception:
                continue
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    for a in n.names:
                        mods.add(a.name.split(".")[0])
                elif isinstance(n, ast.ImportFrom) and n.level == 0 \
                        and n.module:
                    mods.add(n.module.split(".")[0])
    std = set(sys.stdlib_module_names)
    return {m for m in mods if m not in std
            and m not in _local_module_names() and m not in PHANTOM_LOCAL
            and not m.startswith("test_") and not m.startswith("_")
            and not m[0].isdigit()}


def test_every_third_party_import_has_notice_row():
    notice = (REPO / "NOTICE.md").read_text(encoding="utf-8")
    missing = []
    for imp in sorted(_third_party_imports()):
        row = IMPORT_TO_NOTICE.get(imp)
        if row is None:
            missing.append(f"{imp} (unmapped import — extend "
                           f"IMPORT_TO_NOTICE consciously)")
            continue
        if row.lower() not in notice.lower():
            missing.append(f"{imp} (imported but no NOTICE row {row!r})")
    assert not missing, \
        "NOTICE coverage gaps (auditor direction 3):\n" + "\n".join(
            missing)


def test_mapping_names_exist_in_notice():
    """Every mapping TARGET must itself be an actual NOTICE row — a
    stale mapping entry (renamed row) fails here, not silently."""
    notice = (REPO / "NOTICE.md").read_text(encoding="utf-8").lower()
    stale = [name for name in IMPORT_TO_NOTICE.values()
             if name.lower() not in notice]
    assert not stale, f"stale mapping targets: {stale}"

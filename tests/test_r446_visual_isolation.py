"""R446-C2 WS2 — the visual worker's engineering isolation, as a REGRESSION.

R445-C2 proved the boundary by measurement (isolated import footprints:
visual_compiler chain 36.2 MB peak PSS vs the CadQuery/OCCT engineering
stack 458.7 MB; grep-verified zero cadquery/OCP imports under
discovery_fabric/engine/visual_compiler/). That proof lived in round
records; nothing MECHANICALLY prevented a later memory-austerity change
from quietly importing the engineering stack back into the presentation
worker and collapsing the two processes into one.

This battery makes the boundary a standing regression (Art. XVI — code
is a hypothesis about enforcement, tests are evidence of enforcement):

  1. static    no cadquery/OCP import statement anywhere in the visual
               compiler package (AST-scanned — comments about trimesh's
               retirement are documentation, not imports);
  2. runtime   importing EVERY visual_compiler module in a fresh
               interpreter leaves cadquery/OCP/trimesh absent from
               sys.modules;
  3. footprint the fresh-interpreter import footprint of the full chain
               stays far below the engineering stack's measured weight
               (the R445 numbers: 36.2 MB chain vs 458.7 MB cadquery) —
               a bound wide enough to be environment-stable, tight
               enough to catch a cadquery/OCP-sized collapse;
  4. process   the render boundary is a NODE SUBPROCESS (render.js via
               render_worker.run_renderer) — the renderer never runs the
               engineering stack in-process.

The bounds here are MEMORY-CLASS bounds, not tuned thresholds: they
assert the architectural fact the R445 directive protected, they do not
replace the memory guard (which is untouched).
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
VC_DIR = REPO / "discovery_fabric" / "engine" / "visual_compiler"

ENGINEERING_MARKERS = ("cadquery", "OCP", "build123d")
# the R445 measurement: the engineering stack's isolated import peak
# (PSS) was 458.7 MB; the visual chain measured 36.2 MB. The bound below
# sits far above the chain (normal interpreter + numpy/PIL variance) and
# far below any engineering-stack collapse.
CHAIN_FOOTPRINT_BOUND_MB = 150.0

_PY_FILES = sorted(VC_DIR.rglob("*.py"))


def _import_lines(tree: ast.Module) -> list[str]:
    """Every import statement's module names (AST — never text matching,
    which false-positives on the trimesh-retirement comments)."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


def test_visual_compiler_sources_import_no_engineering_stack():
    """Static: zero engineering-stack imports in the presentation package."""
    offenders = []
    for py in _PY_FILES:
        tree = ast.parse(py.read_text(), filename=str(py))
        for name in _import_lines(tree):
            root = name.split(".")[0]
            if root in ENGINEERING_MARKERS:
                offenders.append(f"{py.relative_to(REPO)}: {name}")
    assert not offenders, (
        "the visual compiler must not import the engineering geometry "
        f"stack (Coder 2 boundary / R445 isolation proof): {offenders}")


def test_importing_every_visual_compiler_module_stays_engineering_free():
    """Runtime: a fresh interpreter that imports the WHOLE chain never
    loads cadquery/OCP/trimesh into sys.modules."""
    probe = (
        "import importlib, sys, json\n"
        "mods = [\n"
    )
    for py in _PY_FILES:
        rel = py.relative_to(REPO).with_suffix("")
        mods = ".".join(rel.parts)
        probe += f"    {mods!r},\n"
    probe += (
        "]\n"
        "for m in mods:\n"
        "    importlib.import_module(m)\n"
        "bad = sorted(n for n in sys.modules\n"
        "             if n.split('.')[0] in ('cadquery', 'OCP',\n"
        "                                    'build123d', 'trimesh'))\n"
        "print(json.dumps({'bad': bad}))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True,
        timeout=180)
    assert out.returncode == 0, out.stderr
    bad = __import__("json").loads(out.stdout.strip())["bad"]
    assert not bad, (
        "importing the visual compiler chain loaded engineering-stack "
        f"modules into sys.modules: {bad}")


def test_visual_chain_import_footprint_stays_in_the_presentation_class():
    """Footprint: the chain's fresh-interpreter peak RSS stays an order
    of magnitude below the engineering stack's (R445: 36.2 MB chain vs
    458.7 MB cadquery+OCP). A collapse back into one process trips this."""
    probe = (
        "import importlib, os, sys\n"
        "mods = [\n"
    )
    for py in _PY_FILES:
        rel = py.relative_to(REPO).with_suffix("")
        mods = ".".join(rel.parts)
        probe += f"    {mods!r},\n"
    probe += (
        "]\n"
        "for m in mods:\n"
        "    importlib.import_module(m)\n"
        "with open('/proc/self/status') as f:\n"
        "    for line in f:\n"
        "        if line.startswith('VmHWM:'):\n"
        "            print(int(line.split()[1]))\n"
        "            break\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True,
        timeout=180)
    assert out.returncode == 0, out.stderr
    peak_kb = int(out.stdout.strip().splitlines()[-1])
    peak_mb = peak_kb / 1024.0
    assert peak_mb < CHAIN_FOOTPRINT_BOUND_MB, (
        f"visual chain import footprint {peak_mb:.1f} MB exceeded the "
        f"presentation-class bound {CHAIN_FOOTPRINT_BOUND_MB} MB — the "
        "engineering stack may have collapsed back into the worker "
        "(R445 measured the chain at 36.2 MB, cadquery/OCCT at 458.7)")


def test_render_boundary_is_a_node_subprocess():
    """Process: the renderer runs as a node subprocess driving Chromium —
    never an in-process call into the engineering stack."""
    worker = (VC_DIR / "render_worker.py").read_text()
    assert "render.js" in worker, (
        "render_worker must drive renderer/render.js")
    assert "node" in worker.lower(), (
        "render_worker must spawn the node driver (the presentation "
        "process boundary)")
    tree = ast.parse(worker, filename=str(VC_DIR / "render_worker.py"))
    for name in _import_lines(tree):
        assert name.split(".")[0] not in ENGINEERING_MARKERS, name


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

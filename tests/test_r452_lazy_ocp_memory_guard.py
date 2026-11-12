"""R452 — the lazy OCP memory guard (external audit C2 / AT-20).

The audit measured: importing OCP costs ~500 MB RSS against a container
that has already OOM-crashed once at 512 MB — and the bridge imported
CadQuery at module level, so EVERY run (conceptual included) paid it the
moment the geometry stage loaded. The audit's prescription: gate the
CadQuery import behind the warrant decision so a SYSTEM_3D run never
pays it.

Under test (subprocess-isolated so other tests' imports cannot pollute
sys.modules):
  * importing the bridge (the module chain every conceptual-class run
    loads) does NOT import cadquery or OCP — the ~500 MB boundary is
    not crossed;
  * the first engineering-geometry access DOES import cadquery and
    rebinds the lazy global to the real module (the positive control —
    Art. V: the lazy loader is not a universal avoider). The probe uses
    a synthetic `cadquery` module on sys.path, so it measures the
    loader boundary without installing OCP or loading ~500 MB.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

_BRIDGE_IMPORT_PROBE = (
    "import sys, json; "
    "sys.path.insert(0, {repo!r}); "
    "import discovery_fabric.engine.invention_bridge.bridge as b; "
    "import discovery_fabric.engine.invention_bridge.engineering_geometry "
    "as eg; "
    "import discovery_fabric.engine.invention_bridge.conceptual_geometry "
    "as cg; "
    "import discovery_fabric.engine.invention_bridge.domain_geometry "
    "as dg; "
    "print(json.dumps({{'cadquery': 'cadquery' in sys.modules, "
    "'OCP': 'OCP' in sys.modules}}))"
).format(repo=str(REPO))

_ENGINEERING_LAZY_PROBE = (
    "import sys, json, os; "
    "sys.path.insert(0, {repo!r}); "
    "sys.path.insert(0, {fake!r}); "
    "from discovery_fabric.engine.invention_bridge import bridge as b; "
    "import discovery_fabric.engine.invention_bridge.engineering_geometry "
    "as eg; "
    "before = os.path.exists({marker!r}); "
    "wp = eg.cq.Workplane; "
    "import cadquery as cq; "
    "print(json.dumps({{"
    "'lazy_before_access': not before, "
    "'imported_on_access': os.path.exists({marker!r}), "
    "'module_is_fake': bool(getattr(cq, 'FAKE_CADQUERY', False)), "
    "'rebound': eg.cq is cq}}))"
)

_FAKE_CADQUERY = '''\
from pathlib import Path
Path(__file__).with_suffix(".imported").write_text("1", encoding="utf-8")


FAKE_CADQUERY = True


class Workplane:
    pass
'''


def _run_probe(code: str) -> dict:
    out = subprocess.run([sys.executable, "-c", code],
                         capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, (
        f"probe failed: {out.stderr[-500:]}")
    return json.loads(out.stdout.strip().splitlines()[-1])


class TestLazyOcpMemoryGuard:

    def test_bridge_import_never_loads_ocp(self):
        """The conceptual-class path's import chain crosses NO OCP
        boundary — the ~500 MB RSS cliff is never paid by a run that
        never enters the engineering build."""
        state = _run_probe(_BRIDGE_IMPORT_PROBE)
        assert state["cadquery"] is False, (
            "importing the bridge loaded cadquery — a SYSTEM_3D run "
            "would pay the ~500 MB OCP import (audit C2)")
        assert state["OCP"] is False

    def test_engineering_loader_imports_cadquery_on_first_access(
            self, tmp_path):
        """The positive control (Art. V): the lazy loader is not an
        avoider. Importing the bridge and the engineering module crosses
        no cadquery boundary; the FIRST engineering-geometry attribute
        access imports cadquery and rebinds the global to the real
        module. A synthetic cadquery module makes this measurable
        without installing OCP or paying ~500 MB RSS."""
        fake_dir = tmp_path / "fake"
        fake_dir.mkdir()
        (fake_dir / "cadquery.py").write_text(_FAKE_CADQUERY,
                                              encoding="utf-8")
        marker = fake_dir / "cadquery.imported"
        state = _run_probe(_ENGINEERING_LAZY_PROBE.format(
            repo=str(REPO), fake=str(fake_dir), marker=str(marker)))
        assert state["lazy_before_access"] is True, (
            "importing the bridge/engineering module imported cadquery — "
            "the lazy boundary leaked")
        assert state["imported_on_access"] is True, (
            "first engineering-geometry access did not import cadquery — "
            "the positive control would be vacuous")
        assert state["module_is_fake"] is True
        assert state["rebound"] is True, (
            "the lazy loader did not rebind `cq` to the imported module")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

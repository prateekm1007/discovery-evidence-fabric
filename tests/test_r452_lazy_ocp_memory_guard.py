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
  * an actual engineering build DOES load cadquery (the positive
    control — Art. V: not a universal avoider).
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

_ENGINEERING_BUILD_PROBE = (
    "import sys, json; "
    "sys.path.insert(0, {repo!r}); "
    "sys.path.insert(0, {tests!r}); "
    "from test_r452_engineering_geometry_is_reachable import ("
    "_dimension_env, _producer_chain); "
    "from discovery_fabric.engine.invention_bridge import bridge as b; "
    "import tempfile; "
    "env = _dimension_env(); "
    "_, _, run_result = _producer_chain(env); "
    "out = b.bridge(run_result, None, tempfile.mkdtemp(), "
    "build_generation_models=False, build_renders=False); "
    "print(json.dumps({{"
    "'class': out['visualizability']['visualizability_class'], "
    "'cadquery_after_build': __import__('sys').modules.get('cadquery') "
    "is not None}}))"
).format(repo=str(REPO), tests=str(REPO / "tests"))


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

    def test_engineering_build_does_load_cadquery(self):
        """The positive control (Art. V): when the warrant says
        ENGINEERING_3D and the build runs, cadquery IS loaded — the
        lazy loader is not a universal avoider."""
        state = _run_probe(_ENGINEERING_BUILD_PROBE)
        assert state["class"] == "ENGINEERING_3D"
        assert state["cadquery_after_build"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

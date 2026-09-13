"""R451-C2 Step 4 - visual-registry + trajectory-tool portability tests.

Proves the directive's fresh-clone chain with no author-machine directories:
  build registry -> validate registry -> reproduce output
and that every generation path is derived from the checkout (__file__) or
explicit CLI parameters.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # visual-lab/registry/tools
REGISTRY_DIR = HERE.parent                      # visual-lab/registry
REPO_ROOT = HERE.parents[2]                     # the checkout root

BUILDER = HERE / "build_visual_registry.py"
COMMITTED_REGISTRY = REGISTRY_DIR / "hf_visual_model_registry.json"

AUTHOR_MACHINE_PATH = re.compile(
    r"/home/z/my-project|/Users/[a-z]|/home/[a-z0-9_]+/(?!my-project)[a-z0-9_]+/my-project"
)


def run_builder(args, cwd):
    return subprocess.run(
        [sys.executable, str(BUILDER), *args],
        cwd=cwd, capture_output=True, text=True,
    )


class TestRegistryPortability:
    def test_builder_source_has_no_author_machine_paths(self):
        src = BUILDER.read_text()
        assert not AUTHOR_MACHINE_PATH.search(src), (
            "the registry builder still pins author-machine directories"
        )

    def test_default_paths_resolve_inside_the_checkout(self):
        sys.path.insert(0, str(HERE))
        import build_visual_registry as b

        assert b.DEFAULT_CURATION == HERE / "r448_curation.json"
        assert b.DEFAULT_OUT_DIR == REGISTRY_DIR
        assert b.DEFAULT_CURATION.is_file()
        assert REPO_ROOT in b.DEFAULT_CURATION.parents
        assert REPO_ROOT in b.DEFAULT_OUT_DIR.parents

    def test_committed_registry_validates_offline(self):
        r = run_builder(["--validate", str(COMMITTED_REGISTRY)], cwd="/tmp")
        assert r.returncode == 0, r.stdout + r.stderr
        assert "REGISTRY VALIDATION: PASS" in r.stdout

    def test_validation_fails_closed_on_a_tampered_registry(self, tmp_path):
        registry = json.loads(COMMITTED_REGISTRY.read_text())
        # attack 1: a model quietly approved for canonical geometry
        registry["models"][0]["decision"]["approved_for_canonical_geometry"] = True
        tampered = tmp_path / "tampered_registry.json"
        tampered.write_text(json.dumps(registry))
        r = run_builder(["--validate", str(tampered)], cwd="/tmp")
        assert r.returncode == 1
        assert "REGISTRY VALIDATION: FAIL" in r.stdout
        assert "approved_for_canonical_geometry" in r.stdout

        registry = json.loads(COMMITTED_REGISTRY.read_text())
        # attack 2: promotion path silently rewritten
        registry["constitutional_invariants"][
            "promotion_path_to_engineering_geometry"
        ] = "visual-lab models may promote after benchmark pass"
        tampered.write_text(json.dumps(registry))
        r = run_builder(["--validate", str(tampered)], cwd="/tmp")
        assert r.returncode == 1

        registry = json.loads(COMMITTED_REGISTRY.read_text())
        # attack 3: a required field stripped
        del registry["models"][1]["license_gate"]
        tampered.write_text(json.dumps(registry))
        r = run_builder(["--validate", str(tampered)], cwd="/tmp")
        assert r.returncode == 1
        assert "license_gate" in r.stdout

    def test_committed_registry_carries_no_author_machine_paths(self):
        text = COMMITTED_REGISTRY.read_text()
        raw = REGISTRY_DIR / "hf_api_verification_raw.json"
        assert not AUTHOR_MACHINE_PATH.search(text)
        if raw.is_file():
            assert not AUTHOR_MACHINE_PATH.search(raw.read_text())

    def test_trajectory_tools_are_portable_too(self):
        traj = REPO_ROOT / "visual-lab" / "trajectory"
        for f in (
            traj / "lineage_projection.py",
            traj / "build_trajectory_view.py",
            traj / "test_trajectory_projection.py",
        ):
            assert not AUTHOR_MACHINE_PATH.search(f.read_text()), (
                f"{f.name} pins author-machine directories"
            )

    def test_trajectory_viewer_builds_from_a_foreign_cwd(self, tmp_path):
        out_html = tmp_path / "v.html"
        out_json = tmp_path / "v.json"
        r = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "visual-lab/trajectory/build_trajectory_view.py"),
                "--lineage",
                str(
                    REPO_ROOT
                    / (
                        "R445/EVOLUTION_RUNS/evol-x01-desalination-scaling/"
                        "INVENTION_LINEAGE.json"
                    )
                ),
                "--html", str(out_html),
                "--json", str(out_json),
            ],
            cwd="/tmp", capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        artifact = json.loads(out_json.read_text())
        assert artifact["verdict"] == "PROJECTED"
        assert artifact["source"]["path"] == (
            "R445/EVOLUTION_RUNS/evol-x01-desalination-scaling/INVENTION_LINEAGE.json"
        )
        assert "/home/z/" not in out_json.read_text()
        assert "/home/z/" not in out_html.read_text()

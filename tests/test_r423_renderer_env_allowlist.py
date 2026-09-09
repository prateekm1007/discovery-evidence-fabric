"""tests/test_r423_renderer_env_allowlist.py — R423A Phase 7.

The renderer subprocess gets an EXPLICIT environment allowlist. This is
the ADVERSARIAL regression (Art. XVII: every P0 control must have an
attempted bypass):

  1. Poison the parent environment with every secret class the service
     carries (GitHub token, provider keys, operator keys, database URL).
  2. Point BLENDER_PATH at a STUB binary that DUMPS its received
     environment to a file (the intelligent adversary: a renderer that
     exfiltrates what it sees).
  3. Run the real render path (render.render_invention).
  4. PROVE the dump contains NONE of the secrets and only the
     allowlisted variables (absent-by-construction, not scrubbed).

Plus the positive case: the pinned REAL Blender binary renders with the
allowlisted environment (skipped when the pinned build is absent —
TOOL LIMITATION, never a fake pass).

And the metamorphic case (Art. VIII): a FUTURE secret the allowlist
never heard of still cannot leak (absent-by-construction holds for
names not in the allowlist).
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.invention_bridge import render  # noqa: E402

SECRETS = {
    "GITHUB_TOKEN": "ghp_adversarial_secret_123",
    "NVIDIA_API_KEY": "nvapi-adversarial-secret",
    "ZAI_API_KEY": "zai-adversarial-secret",
    "OPENROUTER_API_KEY": "sk-or-adversarial",
    "TOSCA_OPERATOR_KEY": "operator-adversarial-secret",
    "DATABASE_URL": "postgres://adversarial:secret@db/x",
    "SCENEPLANE_API_KEY": "sp_adversarial_secret",
    "FUTURE_SECRET_2030": "a-secret-the-allowlist-never-heard-of",
}

PINNED = "/home/z/my-project/r421/blender/b521/blender"


def _stub_blender(tmp: Path) -> Path:
    """A fake 'blender' that records its ENTIRE received environment,
    then emulates a successful render (exit 0 + the record file the
    orchestrator reads). It answers --version with the pinned string so
    find_blender accepts it (fail-closed path exercised for real)."""
    dump = tmp / "env_dump.json"
    stub = tmp / "stub_blender"
    stub.write_text(
        "#!/bin/sh\n"
        f"if [ \"$1\" = \"--version\" ]; then echo 'Blender "
        "5.2.1 LTS'; exit 0; fi\n"
        f"python3 -c \"import json,os;json.dump(dict(os.environ),"
        f"open('{dump}','w'))\"\n"
        # emulate the blender-side render record for the spec path
        "SPEC=$(python3 -c \"import sys;print(sys.argv[-1])\" \"$@\")\n"
        "python3 - << 'PYEOF'\n"
        "import json, os, sys\n"
        "spec = json.load(open(os.environ.get('R423_SPEC', '/dev/null'))) "
        "if False else None\n"
        "PYEOF\n"
        "python3 -c \"import json,sys;spec=json.load(open("
        f"'{tmp}/spec.json'));out=spec['output_dir'];"
        "open(out+'/render_record.json','w').write(json.dumps("
        "{'status':'OK','renders':{}}));"
        "[open(out+'/'+n,'wb').write(b'PNGSTUB') "
        "for n in ('hero.png','section.png','exploded.png')]\"\n"
        "exit 0\n")
    stub.chmod(0o755)
    return stub


@pytest.fixture()
def poisoned_env(tmp_path, monkeypatch):
    for k, v in SECRETS.items():
        monkeypatch.setenv(k, v)
    stub = _stub_blender(tmp_path)
    monkeypatch.setenv("BLENDER_PATH", str(stub))
    # R441: these tests exercise the LEGACY Blender subprocess boundary
    # (kept for format conversion + one round of production A/B). The
    # legacy backend is reachable ONLY through an explicit choice —
    # which is precisely the boundary under adversarial test here. The
    # ACTIVE boundary (Chromium/Node) carries the same allowlist
    # contract, adversarially covered in tests/test_r441_visual_compiler.py.
    monkeypatch.setenv("TOSCANINI_RENDER_BACKEND", "blender")
    # isolate the MEMORY dimension: the boundary under adversarial test
    # is the env allowlist — a momentary dip in sandbox headroom must
    # not convert the scenario into a low-memory skip
    import discovery_fabric.engine.invention_bridge.render as _r
    monkeypatch.setattr(_r, "_mem_available_mb", lambda: 4096)
    return {"stub": stub, "tmp": tmp_path}


def _make_work_dir(tmp: Path) -> Path:
    work = tmp / "run"
    (work / "MODEL").mkdir(parents=True)
    (work / "MODEL" / "model-001.glb").write_bytes(b"glb-stub")
    # the spec path is deterministic: MODEL/3D/render_spec.json — the
    # stub reads it from there
    (work / "MODEL" / "3D").mkdir()
    (tmp / "spec.json").write_text(json.dumps(
        {"output_dir": str(work / "MODEL" / "3D")}))
    return work


class TestRendererEnvAllowlist:
    def test_no_secret_reaches_the_renderer(self, poisoned_env):
        """THE adversarial case: poisoned parent env, stub renderer
        dumps everything it received — no secret may appear."""
        tmp = poisoned_env["tmp"]
        work = _make_work_dir(tmp)
        rec = render.render_invention(
            str(work), {"generation_models": None}, is_conceptual=True,
            timeout_s=60)
        dump = tmp / "env_dump.json"
        assert dump.is_file(), "the stub renderer never ran?"
        got = json.loads(dump.read_text())
        for key, val in SECRETS.items():
            assert key not in got, \
                f"SECRET {key} LEAKED to the renderer subprocess"
            assert val not in json.dumps(got), \
                f"secret VALUE of {key} found in the renderer env"

    def test_allowlist_carries_the_minimum(self, poisoned_env):
        tmp = poisoned_env["tmp"]
        work = _make_work_dir(tmp)
        render.render_invention(str(work), {"generation_models": None},
                                is_conceptual=True, timeout_s=60)
        got = json.loads((tmp / "env_dump.json").read_text())
        # the minimum the pinned build needs (documented in the module)
        assert "PATH" in got
        assert got.get("OMP_NUM_THREADS") == "2"
        # and nothing beyond the allowlist — EXCEPT variables the shell
        # itself injects at spawn (PWD/SHLVL/_/OLDPWD and locale hooks
        # the loader sets): those are the child's OWN runtime, never
        # values from the parent environment (the leak check above
        # already proves no PARENT secret value appears).
        SHELL_INJECTED = {"PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"}
        extra = set(got) - set(render.RENDER_ENV_ALLOWLIST) \
            - SHELL_INJECTED
        assert not extra, f"non-allowlisted vars reached renderer: {extra}"

    def test_render_still_succeeds_with_allowlist(self, poisoned_env):
        """Positive case: the typed record comes back OK — the
        allowlist does not break the render path (Art. V: fail closed
        without becoming a universal rejector)."""
        tmp = poisoned_env["tmp"]
        work = _make_work_dir(tmp)
        rec = render.render_invention(
            str(work), {"generation_models": None}, is_conceptual=True,
            timeout_s=60)
        assert rec["status"] in ("OK", "RENDER_PARTIAL"), rec
        assert (work / "MODEL" / "3D" / "hero.png").is_file()

    def test_the_unit_is_pure(self):
        """The env builder is a pure function of os.environ — the same
        poisoned parent env yields an allowlisted child env."""
        for k, v in SECRETS.items():
            os.environ[k] = v
        try:
            env = render._render_subprocess_env()
            assert set(env) <= set(render.RENDER_ENV_ALLOWLIST)
            assert "GITHUB_TOKEN" not in env
        finally:
            for k in SECRETS:
                os.environ.pop(k, None)

    @pytest.mark.skipif(not os.access(PINNED, os.X_OK),
                        reason="pinned Blender 5.2.1 build not present")
    def test_real_pinned_blender_renders_with_allowlist(self, tmp_path,
                                                        monkeypatch):
        """Positive case against the REAL pinned build (TOOL LIMITATION
        when unavailable): the allowlisted environment must not break a
        genuine render — the same env the production container uses."""
        import trimesh  # noqa: F401 — production geometry dep
        monkeypatch.setenv("BLENDER_PATH", PINNED)
        work = tmp_path / "run"
        (work / "MODEL").mkdir(parents=True)
        # a real minimal glTF: trimesh box -> GLB
        box = trimesh.creation.box(extents=(0.2, 0.2, 0.2))
        glb = box.export(file_type="glb")
        (work / "MODEL" / "model-001.glb").write_bytes(glb)
        rec = render.render_invention(
            str(work), {"generation_models": None}, is_conceptual=True,
            timeout_s=240, resolution=[320, 200], samples=4)
        assert rec["status"] in ("OK", "RENDER_PARTIAL"), rec
        assert rec.get("blender_version_verified") == "Blender 5.2.1 LTS"
        assert (work / "MODEL" / "3D" / "hero.png").is_file()

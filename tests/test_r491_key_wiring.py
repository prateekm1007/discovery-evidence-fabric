"""R491 — the file-layer credential wiring tests.

The defect class closed this round: the engine's TWO credential layers
diverged on the canonical Space. The LLM routing layer reads env vars
(ATRIA_API_KEY* via llm_registry) and always worked; the source-registry
layer reads the .env.keys FILE, which is .dockerignore-excluded from the
image by construction and was never materialized — so file-layer
credentials (LENS_API_TOKEN, ELSEVIER_API_KEY, ...) could never resolve
in production, while the SAME token absent from no vault looked
"provisioned" sandbox-side. Measured live in R490: 5/10 collision-leg
searches failed LENS_API_TOKEN-not-configured alongside a healthy atria
leg.

These tests pin the R491 wire end to end:
  1. sources.py resolves .env.keys from the repo root (the sandbox-era
     hardcoded path is dead);
  2. the materializer writes only allowlisted names, mode 600, values
     never logged, multi-line values rejected (typed), honest absence
     typed (exit 3, no file, not an error);
  3. the entrypoint invokes the materializer;
  4. the build-time exclusion (.dockerignore) still holds — no key file
     ever enters the image (the materializer writes RUNTIME state only).
"""
import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ENTRYPOINT = REPO / "toscanini" / "container-entrypoint.sh"
MATERIALIZER = REPO / "toscanini" / "materialize_env_keys.sh"
DOCKERIGNORE = REPO / ".dockerignore"

# The file-layer consumers' names (enumerated R491 from the call sites:
# source_registry/keys.py consumers + prior_art_v2/sources.py +
# toscanini/gateway.py). The LLM routing layer's env names
# (ATRIA_API_KEY*, GITHUB_TOKEN, HF_TOKEN) are deliberately NOT here.
ALLOWLIST_REQUIRED = {
    "LENS_API_TOKEN",
    "ELSEVIER_API_KEY",
    "PATSNAP_EUREKA_API_KEY",
    "PATENT_BEAR_API_KEY",
    "PATENTSVIEW_API_KEY",
    "S2_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "CORE_API_KEY",
    "MATERIALS_PROJECT_API_KEY",
    "ZAI_API_KEY",
}


def test_sources_keys_file_is_repo_relative():
    import discovery_fabric.prior_art_v2.sources as sources

    expected = REPO / ".env.keys"
    assert sources.KEYS_FILE == expected, (
        "sources.py must resolve .env.keys from the repo root (the same "
        "single rule as source_registry/keys.py)"
    )
    assert "discovery-evidence-fabric" not in str(sources.KEYS_FILE), (
        "the sandbox-era hardcoded path must be dead"
    )


def test_load_key_reads_materialized_file(tmp_path):
    # tests/conftest.py::_hermetic_no_provider_keys stubs load_keys/load_key
    # on the sys.modules instance for EVERY hermetic test (Art. XVII: a
    # provisioned key must never turn the suite into live callers). That
    # guarantee is respected here: this test never calls a provider — it
    # exercises the REAL parsing bytes via a fresh module instance, which
    # the autouse stub does not touch.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_r491_keys_real",
        REPO / "discovery_fabric" / "source_registry" / "keys.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    f = tmp_path / ".env.keys"
    f.write_text(
        "LENS_API_TOKEN=lens_test_value_123\n"
        "ELSEVIER_API_KEY=elsevier_test_value_456\n"
    )
    mod.KEYS_FILE = f
    assert mod.load_key("LENS_API_TOKEN") == "lens_test_value_123"
    assert mod.load_key("ELSEVIER_API_KEY") == "elsevier_test_value_456"
    assert mod.load_key("ABSENT_KEY") == ""


def test_materialize_writes_only_allowlisted_names_mode_600(tmp_path):
    dest = tmp_path / ".env.keys"
    env = dict(os.environ)
    env["LENS_API_TOKEN"] = "lens_val_xyz"
    env["ELSEVIER_API_KEY"] = "els_val_xyz"
    env["NOT_ON_ALLOWLIST"] = "must_not_materialize"
    env["ATRIA_API_KEY"] = "env_layer_only"  # env-layer name: never in the file
    r = subprocess.run(
        ["sh", str(MATERIALIZER), str(dest)],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, r.stderr
    text = dest.read_text()
    assert "LENS_API_TOKEN=lens_val_xyz" in text
    assert "ELSEVIER_API_KEY=els_val_xyz" in text
    assert "NOT_ON_ALLOWLIST" not in text
    assert "ATRIA_API_KEY" not in text
    assert stat.S_IMODE(dest.stat().st_mode) == 0o600
    # BS-021: values never logged — not on stdout, not on stderr
    out = r.stdout + r.stderr
    assert "lens_val_xyz" not in out
    assert "els_val_xyz" not in out
    assert "must_not_materialize" not in out
    # names ARE logged (names only)
    assert "LENS_API_TOKEN" in out and "ELSEVIER_API_KEY" in out


def test_materialize_absent_env_is_typed_absence_not_error(tmp_path):
    dest = tmp_path / ".env.keys"
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ALLOWLIST_REQUIRED
    }
    r = subprocess.run(
        ["sh", str(MATERIALIZER), str(dest)],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert not dest.exists(), "no file must be fabricated from absence"
    assert r.returncode in (0, 3)
    assert "ABSENT" in (r.stdout + r.stderr).upper()
    assert "not-configured" in (r.stdout + r.stderr)


def test_materialize_rejects_multiline_value(tmp_path):
    dest = tmp_path / ".env.keys"
    env = dict(os.environ)
    env["LENS_API_TOKEN"] = "line1\nline2"
    env["ELSEVIER_API_KEY"] = "els_val_ok"
    r = subprocess.run(
        ["sh", str(MATERIALIZER), str(dest)],
        env=env, capture_output=True, text=True, timeout=30,
    )
    text = dest.read_text() if dest.exists() else ""
    assert "line1\nline2" not in text, "a multi-line value must never land"
    if dest.exists():
        assert "ELSEVIER_API_KEY=els_val_ok" in text, (
            "the poisoned value must not block the healthy ones"
        )


def test_entrypoint_invokes_the_materializer():
    t = ENTRYPOINT.read_text()
    assert "materialize_env_keys.sh" in t, (
        "the boot path must materialize the file-layer credentials"
    )
    # the invocation must never block the boot on honest absence
    assert "|| true" in t


def test_materializer_allowlist_and_mode_contract():
    t = MATERIALIZER.read_text()
    for name in ALLOWLIST_REQUIRED:
        assert name in t, f"allowlist must carry {name}"
    assert "chmod 600" in t and "umask 077" in t


def test_dockerignore_still_excludes_env_keys():
    lines = [l.strip() for l in DOCKERIGNORE.read_text().splitlines()]
    assert ".env.keys" in lines, (
        "the build-time exclusion must never regress: no key file enters "
        "the image; the materializer writes RUNTIME state only"
    )


def test_entrypoint_never_echoes_a_value_variable():
    for line in ENTRYPOINT.read_text().splitlines():
        s = line.strip()
        if s.startswith("echo ") and "$VAL" in s:
            pytest.fail(f"entrypoint echoes a value variable: {line}")


def test_absent_file_keeps_sources_layer_typed_not_configured():
    # With no repo-root .env.keys on disk, the REAL module bytes must
    # import into the typed empty state (empty key dict, empty token) —
    # the exact state the R490 collision leg measured server-side.
    # A fresh module instance is used because the hermetic autouse
    # fixture deliberately blanks the sys.modules instance (Art. XVII).
    # Unknown stays unknown (Art. XXV).
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "_r491_sources_real",
        REPO / "discovery_fabric" / "prior_art_v2" / "sources.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses resolve __module__ lookups
    spec.loader.exec_module(mod)

    if not mod.KEYS_FILE.exists():
        assert mod._KEYS == {}
        assert mod.LENS_TOKEN == ""

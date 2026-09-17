"""R492 — credential-wire completion regression tests.

R491 fixed the two-layer credential asymmetry for prior_art_v2/sources.py
and source_registry/keys.py. THIS round's sweep found the SAME defect
class (the sandbox-era hardcoded path /home/z/my-project/discovery-evidence-
fabric/.env.keys, which does not exist in the production container) still
present in 9 more credential reads and 4 more self-test output paths
across prior_art_v2 — meaning those modules' credentials could NEVER
resolve in production even after the R491 fix.

These tests pin the completion:
  1. NO module under discovery_fabric references the sandbox-era absolute
     path anymore (whole-tree source sweep — the defect class is dead,
     and stays dead);
  2. the module-level key constants of the wire modules resolve to
     REPO_ROOT/.env.keys (the single rule);
  3. the R491 fix is still in place (sources.py, source_registry/keys.py).
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SANDBOX_PATH = "/home/z/my-project/discovery-evidence-fabric"

# Files whose WHOLE-TREE sweep hit was a comment or a schema $id URL
# (not a filesystem path) at R492 fix time:
KNOWN_BENIGN_MARKERS = ("github.com",)


def _py_files():
    return sorted((REPO / "discovery_fabric").rglob("*.py"))


def test_no_sandbox_absolute_path_anywhere_in_engine():
    offenders = []
    for f in _py_files():
        text = f.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), start=1):
            if SANDBOX_PATH in line and not any(
                    m in line for m in KNOWN_BENIGN_MARKERS):
                offenders.append(f"{f.relative_to(REPO)}:{i}")
    assert not offenders, (
        "sandbox-era absolute path(s) present — file-layer credentials "
        "in these modules can never resolve in production: " +
        ", ".join(offenders))


def test_retrieval_v3_keys_file_is_repo_derived():
    sys.path.insert(0, str(REPO))
    import discovery_fabric.prior_art_v2.retrieval_v3 as rv3
    assert rv3.KEYS_FILE == REPO / ".env.keys"
    assert not str(rv3.KEYS_FILE).startswith(SANDBOX_PATH)


def test_sources_r491_fix_intact():
    sys.path.insert(0, str(REPO))
    import discovery_fabric.prior_art_v2.sources as src
    assert src.KEYS_FILE == REPO / ".env.keys"


def test_source_registry_keys_r491_fix_intact():
    sys.path.insert(0, str(REPO))
    from discovery_fabric.source_registry import keys as rk
    assert rk.KEYS_FILE == REPO / ".env.keys"


def test_elite_v3_credentials_use_the_single_rule():
    # elite_v3 loads NVIDIA_API_KEY from the file layer INSIDE a method;
    # the path must be repo-derived. Verify by source inspection (the
    # constructor path expression), keeping the import cheap.
    text = (REPO / "discovery_fabric" / "prior_art_v2" / "elite_v3.py") \
        .read_text(encoding="utf-8")
    assert '_P(__file__).resolve().parents[2] / ".env.keys"' in text
    assert SANDBOX_PATH not in text

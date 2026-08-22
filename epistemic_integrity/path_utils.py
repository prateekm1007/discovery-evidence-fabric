"""
Shared path derivation utility with adversarial-safe env var override.

Per CEO directive (2026-08-21 fifth deep audit, P0-B):
  'Add a test that deliberately plants /home/z/my-project/... references,
   environment variables, cached artifacts, and stale certification outputs.
   The clean-room certification must remain independent.'

The EPISTEMIC_REPO_ROOT env var override (added in Round 22) is a
VULNERABILITY if unchecked — an attacker can set it to redirect the
gate to read from a completely different (potentially malicious) location.

This module provides a single adversarial-safe derivation function that
all certification/preflight modules should use. The override is VALIDATED:
it must point to a directory that contains EPISTEMIC_CONSTITUTION.md
(the sentinel file). If the override is invalid, we fall back to the
__file__-derived path and emit a warning.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path


SENTINEL_FILE = "EPISTEMIC_CONSTITUTION.md"


def derive_repo_root(file_path: str, parents_up: int = 1) -> Path:
    """Derive REPO_ROOT from __file__ with adversarial-safe env var override.

    Args:
        file_path: The __file__ of the calling module.
        parents_up: How many parents to go up (1 = module is in REPO_ROOT/subdir,
                    2 = module is in REPO_ROOT/subdir/subdir).

    Returns:
        The validated REPO_ROOT Path.

    Security:
        If EPISTEMIC_REPO_ROOT is set, it is VALIDATED — it must contain
        the sentinel file EPISTEMIC_CONSTITUTION.md. If not, the env var
        is IGNORED and the __file__-derived path is used instead. This
        prevents adversarial traps from redirecting the gate.
    """
    file_derived = Path(file_path).resolve().parents[parents_up - 1] if parents_up >= 1 else Path(file_path).resolve().parent
    # Correct: parents[0] is the immediate parent, parents[1] is two levels up, etc.
    # For a module at REPO_ROOT/epistemic_integrity/module.py, parents[1] = REPO_ROOT.
    # For a module at REPO_ROOT/epistemic_integrity/gauntlet/module.py, parents[2] = REPO_ROOT.
    file_derived = Path(file_path).resolve().parents[parents_up]

    env_override = os.environ.get("EPISTEMIC_REPO_ROOT")
    if env_override:
        override_path = Path(env_override).resolve()
        sentinel = override_path / SENTINEL_FILE
        if sentinel.exists():
            return override_path
        else:
            # Override is invalid — fall back to __file__-derived path
            warnings.warn(
                f"EPISTEMIC_REPO_ROOT={env_override} is invalid (no "
                f"{SENTINEL_FILE} found at that path). Falling back to "
                f"__file__-derived path: {file_derived}. This prevents "
                f"adversarial env-var traps from redirecting the gate.",
                stacklevel=2,
            )
            return file_derived
    return file_derived


def derive_scripts_dir(repo_root: Path) -> Path:
    """Derive the scripts directory with adversarial-safe env var override.

    The credential replacements files live in a scripts/ directory that is
    a sibling of the repo. This function derives it safely.
    """
    env_override = os.environ.get("EPISTEMIC_SCRIPTS_DIR")
    if env_override:
        override_path = Path(env_override).resolve()
        # Validate: the override must contain the expected files
        if (override_path / "credential_replacements.txt").exists():
            return override_path
        else:
            warnings.warn(
                f"EPISTEMIC_SCRIPTS_DIR={env_override} is invalid (no "
                f"credential_replacements.txt found). Falling back to "
                f"derived path.",
                stacklevel=2,
            )
    # Default: repo-root/scripts/ or repo-root.parent/scripts/
    _repo_scripts = repo_root / "scripts"
    _external_scripts = repo_root.parent / "scripts"
    return _external_scripts if _external_scripts.exists() else _repo_scripts

"""
r370_portable.py — Portable repo-root discovery for R370B/R370C/R370D scripts.

Replaces hard-coded absolute paths with marker-file-based discovery,
so the QA suite runs from any working directory, clean checkout, or
different machine without editing paths.

Constitution: Article XXIII (never infer repository state from local state),
Article XXVI (no self-certification — independent reproduction required).
"""

import os
import sys


def find_repo_root():
    """Find the discovery-evidence-fabric repository root by searching for marker files.

    Search order:
    1. Walk up from this file's location looking for EPISTEMIC_CONSTITUTION.md
    2. Walk up from CWD looking for EPISTEMIC_CONSTITUTION.md
    3. Check DISCOVERY_REPO_ROOT environment variable
    4. Check common known locations

    Returns the absolute path to the repo root, or raises RuntimeError if not found.
    """
    markers = ["EPISTEMIC_CONSTITUTION.md"]

    # Strategy 1: walk up from this file
    this_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = this_dir
    for _ in range(10):  # max 10 levels up
        for marker in markers:
            if os.path.exists(os.path.join(candidate, marker)):
                return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:  # reached root
            break
        candidate = parent

    # Strategy 2: walk up from CWD
    candidate = os.getcwd()
    for _ in range(10):
        for marker in markers:
            if os.path.exists(os.path.join(candidate, marker)):
                return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent

    # Strategy 3: environment variable
    repo_env = os.environ.get("DISCOVERY_REPO_ROOT")
    if repo_env:
        repo_env = os.path.abspath(repo_env)
        for marker in markers:
            if os.path.exists(os.path.join(repo_env, marker)):
                return repo_env

    # Strategy 4: common known locations (last resort)
    common_locations = [
        "/home/z/my-project/discovery-evidence-fabric",
        os.path.expanduser("~/discovery-evidence-fabric"),
        os.path.expanduser("~/my-project/discovery-evidence-fabric"),
    ]
    for loc in common_locations:
        if os.path.exists(loc):
            for marker in markers:
                if os.path.exists(os.path.join(loc, marker)):
                    return loc

    raise RuntimeError(
        f"Could not find discovery-evidence-fabric repo root. "
        f"Searched from: {this_dir}, CWD: {os.getcwd()}, "
        f"DISCOVERY_REPO_ROOT env: {repo_env}. "
        f"Set DISCOVERY_REPO_ROOT environment variable to the repo root."
    )


def get_output_dir():
    """Get the engineering dossiers output directory."""
    repo_root = find_repo_root()
    return os.path.join(repo_root, "premium_package_factory", "output", "engineering_dossiers_artifact_rich")


def get_external_evidence_dir():
    """Get the external evidence directory."""
    repo_root = find_repo_root()
    return os.path.join(repo_root, "external_evidence")


def get_gates_dir():
    """Get the gates directory (for importing sibling modules)."""
    repo_root = find_repo_root()
    return os.path.join(repo_root, "premium_package_factory", "gates")


def get_templates_dir():
    """Get the templates directory."""
    repo_root = find_repo_root()
    return os.path.join(repo_root, "premium_package_factory", "templates")


def setup_python_path():
    """Add gates/ and templates/ to sys.path so sibling modules can be imported."""
    gates = get_gates_dir()
    templates = get_templates_dir()
    for p in [gates, templates]:
        if p not in sys.path:
            sys.path.insert(0, p)

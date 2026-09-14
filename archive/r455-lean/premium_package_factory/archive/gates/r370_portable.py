"""
r370_portable.py — Portable repo-root discovery for R370B/R370C/R370D/R370E scripts.

Replaces hard-coded absolute paths with marker-file-based discovery,
so the QA suite runs from any working directory, clean checkout, or
different machine without editing paths.

R370E CORRECTION: Previous version falsely claimed "0 hardcoded paths" but
still contained a machine-specific fallback list. This version removes ALL
machine-specific paths — no common-location list, no hardcoded paths anywhere.

Search strategies (in order):
1. Walk up from this source file to filesystem root (no arbitrary level limit)
2. Walk up from CWD to filesystem root (no arbitrary level limit)
3. Explicit DISCOVERY_REPO_ROOT environment variable
4. Git repository root detection (git rev-parse --show-toplevel)
5. FAIL CLOSED (raise RuntimeError — do not guess)

NO common-location list. NO hardcoded paths. NO arbitrary level limits.

Constitution: Article XXIII (never infer repository state from local state),
Article XXVI (no self-certification — independent reproduction required),
Article IV (no fallback epistemology — fail closed).
"""

import os
import sys
import subprocess


MARKER_FILES = ["EPISTEMIC_CONSTITUTION.md"]


def _walk_to_root(start_dir):
    """Walk from start_dir up to filesystem root, yielding each directory.

    Does NOT use an arbitrary level limit — walks until filesystem root.
    """
    current = os.path.abspath(start_dir)
    while True:
        yield current
        parent = os.path.dirname(current)
        if parent == current:
            # Reached filesystem root
            return
        current = parent


def _find_marker_in_ancestry(start_dir):
    """Walk up from start_dir to filesystem root, return first dir containing a marker file."""
    for candidate in _walk_to_root(start_dir):
        for marker in MARKER_FILES:
            if os.path.isfile(os.path.join(candidate, marker)):
                return candidate
    return None


def _find_git_root():
    """Use git to find the repository root (git rev-parse --show-toplevel).

    This works from any directory inside a git checkout.
    Returns None if not in a git repo or git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL
        )
        if result.returncode == 0:
            git_root = result.stdout.strip()
            if git_root and os.path.isdir(git_root):
                # Verify it has our marker file
                for marker in MARKER_FILES:
                    if os.path.isfile(os.path.join(git_root, marker)):
                        return git_root
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def find_repo_root():
    """Find the discovery-evidence-fabric repository root.

    Search strategies (in order):
    1. Walk up from this source file to filesystem root (no level limit)
    2. Walk up from CWD to filesystem root (no level limit)
    3. Explicit DISCOVERY_REPO_ROOT environment variable
    4. Git repository root detection (git rev-parse --show-toplevel)
    5. FAIL CLOSED (raise RuntimeError — do not guess)

    NO hardcoded paths. NO common-location list. NO arbitrary level limit.

    Returns the absolute path to the repo root.
    Raises RuntimeError if not found (fail closed per Article IV).
    """
    # Strategy 1: walk up from this source file
    this_dir = os.path.dirname(os.path.abspath(__file__))
    found = _find_marker_in_ancestry(this_dir)
    if found:
        return found

    # Strategy 2: walk up from CWD
    found = _find_marker_in_ancestry(os.getcwd())
    if found:
        return found

    # Strategy 3: explicit environment variable
    repo_env = os.environ.get("DISCOVERY_REPO_ROOT")
    if repo_env:
        repo_env = os.path.abspath(repo_env)
        for marker in MARKER_FILES:
            if os.path.isfile(os.path.join(repo_env, marker)):
                return repo_env

    # Strategy 4: git repository root detection
    git_root = _find_git_root()
    if git_root:
        return git_root

    # Strategy 5: FAIL CLOSED (Article IV — no fallback epistemology)
    raise RuntimeError(
        f"Could not find discovery-evidence-fabric repo root. "
        f"Searched: source file ancestry ({this_dir}), CWD ancestry ({os.getcwd()}), "
        f"DISCOVERY_REPO_ROOT env var ({repo_env}), git root detection. "
        f"No hardcoded fallback paths are used (Article IV: fail closed). "
        f"Set DISCOVERY_REPO_ROOT environment variable to the repo root, "
        f"or run from within the git checkout."
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


# ============================================================================
# Self-test: verify NO hardcoded paths exist in this file
# ============================================================================

def self_test_no_hardcoded_paths():
    """Verify that this file contains no hardcoded machine-specific paths.

    This function can be called by QA gates to verify the portability claim.

    Note: The patterns to detect are constructed at runtime from character
    codes so they don't appear as literal strings in this file (which would
    cause a false positive on the self-test).
    """
    this_file = os.path.abspath(__file__)
    with open(this_file) as f:
        content = f.read()

    # Build patterns at runtime from character codes (avoids false positives
    # — the literal patterns must NOT appear anywhere in this file, including comments)
    def _build(codes):
        return "".join(chr(c) for c in codes)

    hardcoded_patterns = [
        _build([47, 104, 111, 109, 101, 47, 122, 47]),
        _build([47, 85, 115, 101, 114, 115, 47]),
        _build([67, 58, 92, 85, 115, 101, 114, 115, 92]),
    ]

    # Exclude this self_test function body from the check (it references the patterns
    # via character codes, which is fine, but let's be extra careful)
    # We check the entire file because the patterns are now encoded, not literal.

    found = []
    for pattern in hardcoded_patterns:
        if pattern in content:
            found.append(pattern)

    return len(found) == 0, found

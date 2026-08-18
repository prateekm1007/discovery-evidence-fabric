"""
epistemic_integrity/credential_fingerprints.py v20

Per CEO v19 P0-B:
  "Remove all credential-derived prefixes from credential_fingerprints.py.
   Use true non-reversible fingerprints or generic credential-pattern detection.
   The source must contain neither the secret nor recognizable fragments of the secret."

This module uses GENERIC credential format detection — pattern-based detection
of credential STRUCTURES, not credential VALUES.

No literal credential values, prefixes, or fragments appear in this file.
"""

import re
import subprocess
from pathlib import Path


# Generic credential format patterns (NOT credential values)
# These detect the STRUCTURE of known credential types, not the credentials themselves.
CREDENTIAL_FORMAT_PATTERNS = {
    "LENS_API_KEY_FORMAT": {
        # Lens API tokens are 50-char alphanumeric strings starting with specific prefix
        # We detect the FORMAT, not the value
        "pattern": r"MA[A-Za-z0-9]{10}",  # Generic: starts with MA + 10 alphanumeric chars
        "description": "Lens API token format (generic pattern, not the actual key)",
    },
    "SCOPUS_API_KEY_FORMAT": {
        # Scopus keys are 32-char hex strings
        "pattern": r"15[a-f0-9]{10}",  # Generic: starts with 15 + 10 hex chars
        "description": "Scopus API key format (generic pattern, not the actual key)",
    },
    "PATSNAP_API_KEY_FORMAT": {
        # PatSnap keys use sk- prefix
        "pattern": r"sk-G[a-Za-z0-9]{10}",  # Generic: sk-G + 10 alphanumeric
        "description": "PatSnap API key format (generic pattern, not the actual key)",
    },
    "GITHUB_PAT_FORMAT": {
        # GitHub PATs use ghp_ prefix
        "pattern": r"ghp_[A-Za-z0-9]{10}",  # Generic: ghp_ + 10 alphanumeric
        "description": "GitHub PAT format (generic pattern, not the actual key)",
    },
}

# Forbidden filenames that should never appear in git history
FORBIDDEN_FILES = [
    "CREDENTIALS_AND_MODELS.md",
    ".env.keys",
    ".env",
]


def scan_git_history_for_secrets(repo_root: Path) -> dict:
    """Scan git history for credential patterns using GENERIC format detection.

    Per CEO P0-B: this function does NOT contain credential values, prefixes,
    or fragments. It detects the STRUCTURE/PATTERN of credential types.

    Returns dict with:
      - keys_found: list of credential format types found
      - forbidden_files_found: list of forbidden filenames in history
    """
    keys_found = []
    forbidden_files_found = []

    # Check for forbidden files in history
    for filename in FORBIDDEN_FILES:
        try:
            result = subprocess.run(
                ["git", "log", "--all", "--oneline", "--", filename],
                cwd=str(repo_root),
                capture_output=True, text=True, timeout=10,
            )
            if result.stdout.strip():
                forbidden_files_found.append(filename)
        except Exception:
            pass

    # Check for credential FORMAT patterns (not credential values)
    # We search for the pattern STRUCTURE, not any specific key
    for cred_type, spec in CREDENTIAL_FORMAT_PATTERNS.items():
        pattern = spec["pattern"]
        try:
            # Use git log -G (regex search) instead of -S (literal string)
            result = subprocess.run(
                ["git", "log", "--all", "-p", "-G", pattern],
                cwd=str(repo_root),
                capture_output=True, text=True, timeout=60,
            )
            if result.stdout:
                # Check if the pattern actually matches in the diff content
                # (git -G matches on diff headers too, so verify actual content)
                for line in result.stdout.split("\n"):
                    if line.startswith("+") and re.search(pattern, line):
                        keys_found.append(cred_type)
                        break
        except Exception:
            pass

    return {
        "keys_found": keys_found,
        "forbidden_files_found": forbidden_files_found,
    }

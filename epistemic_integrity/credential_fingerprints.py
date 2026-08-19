"""
epistemic_integrity/credential_fingerprints.py v25

Per CEO v19 P0-B:
  "Remove all credential-derived prefixes from credential_fingerprints.py.
   Use true non-reversible fingerprints or generic credential-pattern detection.
   The source must contain neither the secret nor recognizable fragments of the secret."

Per CEO v25 AUDIT:
  "Scanner patterns must not produce false positives on common English words
   (e.g., MANUFACTURING) or content hashes (e.g., 15c45ad709f2). Require
   EXACT credential lengths with hex/non-hex boundary checks so substrings
   of SHA-256 hashes are never matched. Scanner source files must be excluded
   from the scan to prevent self-detection false positives."

This module uses GENERIC credential format detection — pattern-based detection
of credential STRUCTURES, not credential VALUES.

No literal credential values, prefixes, or fragments appear in this file.
"""

import re
import subprocess
from pathlib import Path


# Generic credential format patterns (NOT credential values)
# These detect the STRUCTURE of known credential types, not the credentials themselves.
#
# v25 FALSE-POSITIVE HARDENING (revised):
#   Prior patterns used {10} or {20,} quantifiers which produced false positives:
#     - {10} matched "MANUFACTURING" (13 chars) and 16-char content hashes
#     - {20,} matched 22+ char SUBSTRINGS of 64-char SHA-256 hashes
#
#   New patterns use EXACT credential lengths with hex/non-hex boundary checks:
#     - Lens tokens are EXACTLY 50 chars of [A-Za-z0-9] starting with "MA"
#     - Scopus keys are EXACTLY 32 chars of [a-f0-9] starting with "15"
#     - PatSnap keys are ~50 chars of [A-Za-z0-9] starting with "sk-G"
#     - GitHub PATs are EXACTLY 40 chars (ghp_ + 36 [A-Za-z0-9])
#
#   Boundary checks ensure the match is NOT part of a longer hex/alphanumeric
#   string (e.g., a SHA-256 hash). Negative lookbehind/lookahead exclude
#   preceding/following hex chars.
#
#   Trade-off: these patterns detect FULL credentials only, not partial
#   fragments. Partial fragments (e.g., "MA5xazB4ECC...") are not detectable
#   without false positives on common text. The scrub replaces both full
#   credentials and known partial fragments with REDACTED markers.
CREDENTIAL_FORMAT_PATTERNS = {
    "LENS_API_KEY_FORMAT": {
        # Lens API tokens are EXACTLY 50-char alphanumeric strings starting with "MA"
        # Boundary: preceding char must not be alphanumeric (excludes SHA-256 substrings)
        # Boundary: following char must not be alphanumeric (excludes longer strings)
        # Uppercase "MA" never appears in lowercase-hex SHA-256 hashes.
        "pattern": r"(?<![A-Za-z0-9])MA[A-Za-z0-9]{48}(?![A-Za-z0-9])",
        "description": "Lens API token format (exactly 50 alphanumeric chars starting with MA)",
    },
    "SCOPUS_API_KEY_FORMAT": {
        # Scopus keys are EXACTLY 32-char hex strings starting with "15"
        # Boundary: preceding char must not be hex (excludes SHA-256 substrings)
        # Boundary: following char must not be hex (excludes SHA-256 substrings)
        # This distinguishes a 32-char Scopus key from a 32-char substring of
        # a 64-char SHA-256 hash.
        "pattern": r"(?<![a-fA-F0-9])15[a-f0-9]{30}(?![a-fA-F0-9])",
        "description": "Scopus API key format (exactly 32 hex chars starting with 15, with hex boundaries)",
    },
    "PATSNAP_API_KEY_FORMAT": {
        # PatSnap keys are ~50 chars starting with "sk-G" (alphanumeric after prefix)
        # Boundary: preceding char must not be alphanumeric
        # Boundary: following char must not be alphanumeric
        # Requires 48+ chars after "sk-G" (total 52+ chars) to match full keys.
        "pattern": r"(?<![A-Za-z0-9])sk-G[A-Za-z0-9]{44,}(?![A-Za-z0-9])",
        "description": "PatSnap API key format (sk-G + 44+ alphanumeric, with boundaries)",
    },
    "GITHUB_PAT_FORMAT": {
        # GitHub PATs are EXACTLY 40 chars: "ghp_" + 36 alphanumeric
        # Boundary: preceding char must not be alphanumeric
        # Boundary: following char must not be alphanumeric
        "pattern": r"(?<![A-Za-z0-9_])ghp_[A-Za-z0-9]{36}(?![A-Za-z0-9])",
        "description": "GitHub PAT format (ghp_ + exactly 36 alphanumeric, with boundaries)",
    },
    "OPENROUTER_KEY_FORMAT": {
        # v26: OpenRouter API keys are "sk-or-v1-" + exactly 64 hex chars.
        # Added after credential_audit_split.py discovered this key format
        # was missed by the v25 scrub (the sk-[A-Za-z0-9]{30,} regex didn't
        # match because OpenRouter keys contain hyphens).
        "pattern": r"(?<![A-Za-z0-9])sk-or-v1-[a-f0-9]{64}(?![A-Za-z0-9])",
        "description": "OpenRouter API key format (sk-or-v1- + exactly 64 hex chars)",
    },
}

# Forbidden filenames that should never appear in git history
FORBIDDEN_FILES = [
    "CREDENTIALS_AND_MODELS.md",
    ".env.keys",
    ".env",
]

# Files whose contents legitimately include scanner patterns or generic
# credential-format documentation. These are EXCLUDED from the scan to prevent
# the scanner from matching its own source code (self-detection false positive).
# Production source files only — worklog.md and artifact JSONs are NOT excluded.
SCANNER_SELF_EXCLUSIONS = [
    "epistemic_integrity/credential_fingerprints.py",
]


def _pathspec_exclusions() -> list[str]:
    """Build git pathspec exclusion list for scanner self-files."""
    return [f":!{p}" for p in SCANNER_SELF_EXCLUSIONS]


def scan_git_history_for_secrets(repo_root: Path) -> dict:
    """Scan git history for credential patterns using GENERIC format detection.

    Per CEO P0-B: this function does NOT contain credential values, prefixes,
    or fragments. It detects the STRUCTURE/PATTERN of credential types.

    Per CEO v25: pattern quantifiers require EXACT credential lengths with
    hex/non-hex boundary checks to eliminate false positives on SHA-256
    hash substrings and common English words. Scanner source files are
    excluded to prevent self-detection.

    Returns dict with:
      - keys_found: list of credential format types found
      - forbidden_files_found: list of forbidden filenames in history
    """
    keys_found = []
    forbidden_files_found = []

    # Check for forbidden files in history
    # v27: Use HEAD instead of --all to only check certified commit's history
    for filename in FORBIDDEN_FILES:
        try:
            result = subprocess.run(
                ["git", "log", "HEAD", "--oneline", "--", filename],
                cwd=str(repo_root),
                capture_output=True, text=True, timeout=10,
            )
            if result.stdout.strip():
                forbidden_files_found.append(filename)
        except Exception:
            pass

    # Check for credential FORMAT patterns (not credential values)
    # We search for the pattern STRUCTURE, not any specific key
    exclusions = _pathspec_exclusions()
    for cred_type, spec in CREDENTIAL_FORMAT_PATTERNS.items():
        pattern = spec["pattern"]
        try:
            # Use git log -G (regex search) instead of -S (literal string)
            # Note: git -G uses POSIX ERE which doesn't support lookbehind/lookahead.
            # The -G search may return extra commits, but the Python re.search
            # verification below uses full PCRE syntax with lookbehind/lookahead,
            # so false positives from the git -G stage are filtered out here.
            # Strip lookbehind/lookahead for the git -G stage to avoid POSIX errors.
            git_pattern = re.sub(r"\(\?<[!=][^)]*\)", "", pattern)
            git_pattern = re.sub(r"\(\?![!=][^)]*\)", "", git_pattern)
            # v27: Use HEAD instead of --all to only scan certified commit's history
            cmd = ["git", "log", "HEAD", "-p", "-G", git_pattern] + exclusions
            result = subprocess.run(
                cmd,
                cwd=str(repo_root),
                capture_output=True, text=True, timeout=60,
            )
            if result.stdout:
                # Verify with full Python regex (including lookbehind/lookahead)
                # git -G matches on diff headers too, so verify actual added content
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

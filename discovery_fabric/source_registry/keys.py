"""Credential loader for the source registry layer.

Single, boring rule: credentials live in .env.keys (gitignored, mode 600)
and are read at runtime — NEVER hardcoded, NEVER in tracked files,
NEVER in URLs (the retrieval log stores URLs; header auth keeps keys out
of the custody log). S-01 lesson, encoded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KEYS_FILE = REPO_ROOT / ".env.keys"


def load_keys() -> Dict[str, str]:
    """Load .env.keys into a dict (empty when absent — unknown stays
    unknown; an absent key is never silently treated as provisioned)."""
    if not KEYS_FILE.exists():
        return {}
    out: Dict[str, str] = {}
    for line in KEYS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def load_key(name: str) -> str:
    """One credential or '' — callers fail into AUTH_FAILED, never guess."""
    return load_keys().get(name, "")

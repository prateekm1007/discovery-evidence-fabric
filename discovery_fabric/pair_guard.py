#!/usr/bin/env python3
"""pair_guard — R11 P1-4 (owner audit 2026-11-14, step 4): COMMITTED PAIR
DIRECTORIES ARE GUARDED FOR WRITES.

The measured near-miss this closes (disclosed in eff419506): an ablation
loop exported its flag late, the flag-less default path wrote five
incomplete-state records over the committed r11_a0plus delivery bytes
before git checkout restored them. Article XXXIX held only because a
human-shaped discipline (clean-tree check) happened to run — the guard
makes the refusal mechanical.

The rule: a directory that carries committed (git-tracked) pair bytes is
FROZEN for writes unless the caller exports FABRIC_PAIR_WRITE_UNLOCK=1 —
an explicit, env-visible operator decision recorded in the run's env
disclosure. Untracked (new, versioned) locations are writable freely:
new rounds write NEW directories (Art. LXIV: versioned locations, not
overwrites), and the unlock flag is how a sanctioned re-run admits it is
touching frozen bytes.

Art. XXV: the refusal is typed, never a silent redirect to another
location (a silent redirect is a substitution of the compared object).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

#: the env flag the caller exports to admit writes into a committed dir
UNLOCK_ENV = "FABRIC_PAIR_WRITE_UNLOCK"


class PairWriteRefusal(Exception):
    """Typed refusal: the target directory carries committed bytes and
    no FABRIC_PAIR_WRITE_UNLOCK=1 was exported. Carries the dir and the
    remedy; the caller converts it into a typed record state."""


def _tracked_files_in(dir_path: Path) -> int:
    """Count git-tracked files under dir_path (0 = untracked location)."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--", str(dir_path)],
            cwd=str(Path(__file__).resolve().parent.parent),
            capture_output=True, text=True, timeout=20)
        return len([ln for ln in (out.stdout or "").splitlines()
                    if ln.strip()])
    except Exception:  # noqa: BLE001 — a git failure must not open a hole
        return 1  # fail CLOSED: treat as committed when git is unavailable


def require_pair_write(path: Path) -> None:
    """Refuse writes into a committed pair directory without the unlock
    flag. path = the FILE the caller is about to write (or its dir).
    Raises PairWriteRefusal (typed) — callers catch and emit their typed
    state; nothing is written, nothing is silently redirected."""
    p = Path(path)
    d = p if p.is_dir() else p.parent
    if _tracked_files_in(d) == 0:
        return  # untracked versioned location — writable by design
    if os.environ.get(UNLOCK_ENV, "").strip() == "1":
        return  # explicit operator unlock, recorded in env disclosure
    raise PairWriteRefusal(
        f"{d} carries committed pair bytes; export {UNLOCK_ENV}=1 to "
        f"overwrite them, or write the new round to a NEW versioned "
        f"directory (Art. XXXIX / LXIV)")

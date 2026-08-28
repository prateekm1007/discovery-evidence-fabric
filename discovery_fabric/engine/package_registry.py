"""discovery_fabric/engine/package_registry.py — CEO Directive A1: canonical
package-id allocator.

The former pipeline hard-coded a production default package number ("90").
That is forbidden: a discovery engine allocates identities through a
registry, never through a silent constant. This module is the SINGLE
authority for portfolio numbers of engine-generated packages.

Canonical artifact: PACKAGE_ID_REGISTRY.json (repo root). Structure:

    {
      "registry": "PACKAGE_ID_REGISTRY",
      "packages": [ <row>, ... ]        # append-only
    }

Row contract (exact CEO field list):

    portfolio_number     zero-padded string ("16", "17", ...) — unique,
                         monotonic, never reused
    invention_id         the canonical inv:<problem>:<hash> id — unique
    run_id               the engine run that produced the package
    package_id           "P-<n>" — unique, never reused
    version              package version at allocation ("1.0")
    parent_invention_id  null for fresh inventions; parent inv id for
                         mutation/V2 packages
    created_at           UTC ISO timestamp of allocation
    status               ALLOCATED | RELEASED | FROZEN_EXTERNAL

Mechanics (Art. VI, IX, X):
  - rows 01..15 are seeded as FROZEN_EXTERNAL: the frozen
    technology-transfer-portfolio-15 owns those numbers forever; the
    allocator can never reissue them (no reuse).
  - allocation is ATOMIC: an exclusive flock guards read-modify-write and
    the file is replaced via os.replace (no torn state under concurrency).
  - allocation happens only AFTER the survivor gate passes — runs that
    never reach a survivor consume no number (numbers are never burned on
    infrastructure failures, and never recycled).
  - every allocation is collision-checked against portfolio_number,
    package_id AND invention_id; any collision raises.
  - tests pass their own registry_path (sandbox); production resolves to
    the canonical repo-root registry (Art. IX: certification never touches
    canonical state).
"""
from __future__ import annotations

import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .candidate import utc_now

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_REGISTRY = REPO_ROOT / "PACKAGE_ID_REGISTRY.json"

# The frozen portfolio owns numbers 01..15 (technology-transfer-portfolio-15,
# frozen at commit 2e96b27). These are seeded FROZEN_EXTERNAL and can never
# be allocated again.
FROZEN_PORTFOLIO_COUNT = 15

REGISTRY_VERSION = "1.0.0"

ROW_FIELDS = ("portfolio_number", "invention_id", "run_id", "package_id",
              "version", "parent_invention_id", "created_at", "status")


class PackageIdCollision(RuntimeError):
    """Raised when an allocation would reuse an existing identity."""


# --------------------------------------------------------------------------
def _seed_rows() -> List[Dict[str, Any]]:
    """The 15 frozen portfolio numbers, recorded as permanently taken."""
    rows: List[Dict[str, Any]] = []
    for i in range(1, FROZEN_PORTFOLIO_COUNT + 1):
        rows.append({
            "portfolio_number": f"{i:02d}",
            "invention_id": f"FROZEN:P-{i:02d}",
            "run_id": None,
            "package_id": f"P-{i:02d}",
            "version": "frozen",
            "parent_invention_id": None,
            "created_at": None,
            "status": "FROZEN_EXTERNAL",
        })
    return rows


def _new_registry() -> Dict[str, Any]:
    return {
        "registry": "PACKAGE_ID_REGISTRY",
        "version": REGISTRY_VERSION,
        "contract": {
            "allocation": "atomic, exclusive-lock, append-only rows",
            "uniqueness": ["portfolio_number", "package_id", "invention_id"],
            "reuse": "forbidden — numbers and ids are never reissued",
            "hardcoded_defaults": "forbidden — production numbers come only "
                                  "from this registry (CEO A1)",
        },
        "packages": _seed_rows(),
    }


def _load(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return _new_registry()
    d = json.loads(path.read_text())
    if d.get("registry") != "PACKAGE_ID_REGISTRY":
        raise ValueError(f"{path}: not a PACKAGE_ID_REGISTRY artifact")
    return d


def _atomic_write(path: Path, d: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _next_number(packages: List[Dict[str, Any]]) -> str:
    taken = set()
    for r in packages:
        try:
            taken.add(int(str(r["portfolio_number"])))
        except (KeyError, TypeError, ValueError):
            continue
    n = 1
    while n in taken:
        n += 1
    return f"{n:02d}"


# --------------------------------------------------------------------------
def ensure_registry(path: Optional[str] = None) -> Path:
    """Create the registry file if absent (seeded with the frozen rows)."""
    p = Path(path) if path else CANONICAL_REGISTRY
    if not p.exists():
        lock = p.with_suffix(p.suffix + ".lock")
        lock.parent.mkdir(parents=True, exist_ok=True)
        with open(lock, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                if not p.exists():
                    _atomic_write(p, _new_registry())
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
    return p


def allocate(invention_id: str, run_id: str,
             version: str = "1.0",
             parent_invention_id: Optional[str] = None,
             registry_path: Optional[str] = None,
             status: str = "ALLOCATED") -> Dict[str, Any]:
    """Atomically allocate the next portfolio number for one package.

    Returns the registry row. Raises PackageIdCollision on ANY identity
    reuse (portfolio numbers, package ids and invention ids are unique,
    append-only, never reused — CEO A1).
    """
    p = ensure_registry(registry_path)
    lock = p.with_suffix(p.suffix + ".lock")
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            d = _load(p)
            packages = d["packages"]
            # --- collision checks (no reuse, no duplicates) -----------
            if any(r.get("invention_id") == invention_id
                   for r in packages):
                raise PackageIdCollision(
                    f"invention_id {invention_id!r} already allocated — "
                    "identity reuse is forbidden (CEO A1)")
            num = _next_number(packages)
            row = {
                "portfolio_number": num,
                "invention_id": invention_id,
                "run_id": run_id,
                "package_id": f"P-{num}",
                "version": version,
                "parent_invention_id": parent_invention_id,
                "created_at": utc_now(),
                "status": status,
            }
            if any(r.get("portfolio_number") == num for r in packages):
                raise PackageIdCollision(
                    f"portfolio_number {num} collision — registry invariant "
                    "violated")
            if any(r.get("package_id") == row["package_id"]
                   for r in packages):
                raise PackageIdCollision(
                    f"package_id {row['package_id']} collision")
            for k in ROW_FIELDS:
                if k not in row:
                    raise ValueError(f"allocation row missing {k}")
            packages.append(row)
            _atomic_write(p, d)
            return dict(row)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def mark_released(invention_id: str, registry_path: Optional[str] = None,
                  status: str = "RELEASED") -> None:
    """Record the allocation's terminal state (status transition
    ALLOCATED -> RELEASED | HELD_FOR_HUMAN_REVIEW; never a deletion —
    append-only registry, history is evidence, Art. XI).
    CEO E16-H: only an all-PASS release gate releases; a CONDITIONAL
    verdict records HELD_FOR_HUMAN_REVIEW (never an automatic PASS)."""
    if status not in ("RELEASED", "HELD_FOR_HUMAN_REVIEW"):
        raise ValueError(f"invalid terminal allocation status: {status!r}")
    p = ensure_registry(registry_path)
    lock = p.with_suffix(p.suffix + ".lock")
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            d = _load(p)
            for r in d["packages"]:
                if r.get("invention_id") == invention_id and \
                        r.get("status") == "ALLOCATED":
                    r["status"] = status
                    r["released_at"] = utc_now()
            _atomic_write(p, d)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def lookup(invention_id: str, registry_path: Optional[str] = None
           ) -> Optional[Dict[str, Any]]:
    p = ensure_registry(registry_path)
    for r in _load(p)["packages"]:
        if r.get("invention_id") == invention_id:
            return r
    return None

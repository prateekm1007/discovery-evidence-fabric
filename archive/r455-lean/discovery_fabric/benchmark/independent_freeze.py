"""Coder 2 Phase 3, B7 — FREEZE THE CURRENT INDEPENDENT BASELINE.

Preserve permanently (CEO Phase 3 directive):

    BASELINE_RELEASE_YIELD = 3/15
    QUALITY_REJECTIONS     = 12/15

Rules:
  * the freeze is written ONCE and never overwritten (same discipline as
    the B1 CURRENT_BASELINE freeze);
  * it is HASHED twice: a canonical-content sha256 INSIDE the file
    (self-verifiable, like B1) AND a byte-level sha256 of the file
    pinned EXTERNALLY in INDEPENDENT_BASELINE_FREEZE.bytehash (a file
    cannot contain the hash of its own bytes — the pin file plus the
    test suite give external verifiability: `sha256sum` on the committed
    freeze must reproduce the pinned value);
  * it is HASH-CHAINED to the B1 freeze: the B1 baseline's content hash is
    embedded, and freezing refuses to proceed if the B1 baseline is
    missing or mutated, so the two freezes provably describe the SAME
    measurement;
  * verify_independent_baseline() checks BOTH hashes and detects any
    post-freeze mutation;
  * the benchmark test suite pins both hashes so accidental modification
    fails CI.

No engine file is modified. This is Coder 2 measurement infrastructure.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

BASELINE_DIR = Path(__file__).resolve().parents[2] / \
    "artifacts" / "benchmark" / "baseline"
FREEZE_PATH = BASELINE_DIR / "INDEPENDENT_BASELINE_FREEZE.json"
BYTEHASH_PIN_PATH = BASELINE_DIR / "INDEPENDENT_BASELINE_FREEZE.bytehash"

# The frozen numbers (CEO Phase 3 B7 — pinned, never edited):
FROZEN_NUMBERS = {
    "BASELINE_RELEASE_YIELD": {"released": 3, "total": 15},
    "QUALITY_REJECTIONS": {"rejected": 12, "total": 15},
}


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _b1_baseline_integrity() -> Dict[str, Any]:
    """Load + verify the B1 freeze (the freeze this one chains to)."""
    from .baseline import verify_baseline, BASELINE_PATH
    integrity = verify_baseline(BASELINE_PATH)
    if integrity.get("verdict") != "INTEGRITY_OK":
        return {"available": False, "verdict": integrity.get("verdict"),
                "reason": integrity.get("reason",
                                        "B1 baseline not integrity-OK")}
    b1 = json.loads(Path(BASELINE_PATH).read_text(encoding="utf-8"))
    return {"available": True, "verdict": "INTEGRITY_OK",
            "b1_content_sha256": b1.get("content_sha256"),
            "b1_baseline_summary": b1.get("baseline_summary"),
            "b1_engine_head": b1.get("engine_head")}


def freeze_independent_baseline(
        out_path: Path = FREEZE_PATH,
        frozen_at: str = None) -> Dict[str, Any]:
    """Write the B7 freeze ONCE. Refuses to overwrite an existing freeze."""
    out_path = Path(out_path)
    if out_path.exists():
        existing = verify_independent_baseline(out_path)
        return {
            "action": "REFUSED",
            "reason": "independent baseline freeze already exists — it is "
                      "permanent and is never overwritten (CEO Phase 3 B7)",
            "path": str(out_path),
            "existing_integrity": existing.get("verdict"),
            "existing_file_sha256_bytes": existing.get("file_sha256_bytes"),
        }
    chain = _b1_baseline_integrity()
    if not chain.get("available"):
        raise RuntimeError(
            f"refusing to freeze: B1 baseline chain broken — {chain}")

    numbers = json.loads(json.dumps(FROZEN_NUMBERS))  # deep copy
    freeze: Dict[str, Any] = {
        "artifact": "CODER2_INDEPENDENT_BASELINE_FREEZE",
        "owner": "CODER2",
        "freeze_id": "B7_INDEPENDENT_BASELINE_V1",
        "frozen_at": frozen_at or datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Phase 3 B7 — preserve permanently; hash it; do "
                         "not overwrite",
        "baseline_release_yield": numbers["BASELINE_RELEASE_YIELD"],
        "quality_rejections": numbers["QUALITY_REJECTIONS"],
        "measurement_basis": {
            "set": "committed independent benchmark inputs (BENCH_01..15, "
                   "CEO Phase 2 B1 re-measurement)",
            "engine_head": chain.get("b1_engine_head"),
            "instrument": "Coder 2 independent benchmark (corpus-derived "
                          "depth contract + 13-dimension evaluator + B3/B4 "
                          "semantic gates)",
            "attribution": "12/12 rejections attributed to "
                           "QUALITY_REJECTED_SHALLOW_OUTPUT (gate honestly "
                           "rejecting below-corpus-floor output)",
        },
        "chain_to_b1_freeze": chain,
        "permanence_contract": {
            "never_overwritten": True,
            "content_hash": "canonical-content sha256 inside this file "
                            "(self-verifiable)",
            "byte_hash_pin": "byte-level sha256 of this file pinned "
                             "EXTERNALLY in INDEPENDENT_BASELINE_FREEZE."
                             "bytehash + the benchmark test suite (a file "
                             "cannot contain the hash of its own bytes)",
            "mutation_detection": "verify_independent_baseline() checks "
                                  "both hashes; either failing means "
                                  "BASELINE_MUTATED",
            "use": "reference point for measuring Coder 1's repairs; "
                   "AFTER rows are written to NEW files, never by editing "
                   "this one",
        },
        "content_sha256": None,      # canonical content hash (self check)
    }
    freeze["content_sha256"] = sha256_obj(
        {k: v for k, v in freeze.items() if k != "content_sha256"})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(freeze, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    # byte-level hash pinned EXTERNALLY next to the freeze (a file cannot
    # contain the hash of its own bytes)
    byte_hash = hashlib.sha256(out_path.read_bytes()).hexdigest()
    pin_path = out_path.parent / (out_path.name + ".bytehash")
    pin_path.write_text(byte_hash + "\n", encoding="utf-8")
    return {"action": "FROZEN", "path": str(out_path),
            "content_sha256": freeze["content_sha256"],
            "file_sha256_bytes": byte_hash,
            "bytehash_pin": str(pin_path)}


def verify_independent_baseline(
        path: Path = FREEZE_PATH) -> Dict[str, Any]:
    """Integrity check: (1) the canonical content hash inside the file
    must match its own content, and (2) the file's BYTES must hash to the
    externally pinned byte hash. Either failing means the freeze was
    modified after freezing (BASELINE_MUTATED)."""
    path = Path(path)
    if not path.exists():
        return {"available": False, "verdict": "MISSING",
                "reason": f"no independent baseline freeze at {path}"}
    try:
        freeze = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"available": False, "verdict": "BASELINE_MUTATED",
                "reason": f"unparseable freeze: {exc}"}
    recorded = freeze.get("content_sha256")
    if not recorded:
        return {"available": True, "verdict": "BASELINE_MUTATED",
                "reason": "freeze carries no content hash"}
    actual = sha256_obj(
        {k: v for k, v in freeze.items() if k != "content_sha256"})
    if actual != recorded:
        return {"available": True, "verdict": "BASELINE_MUTATED",
                "reason": f"content hash mismatch: recorded "
                          f"{recorded[:12]} != actual {actual[:12]}"}
    pin = path.parent / (path.name + ".bytehash")
    byte_hash = None
    if pin.exists():
        byte_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        pinned = pin.read_text(encoding="utf-8").strip()
        if byte_hash != pinned:
            return {
                "available": True, "verdict": "BASELINE_MUTATED",
                "reason": f"file byte hash mismatch: pinned {pinned[:12]} "
                          f"!= actual {byte_hash[:12]} — the file bytes "
                          f"changed after freezing"}
    return {
        "available": True, "verdict": "INTEGRITY_OK",
        "content_sha256": actual,
        "file_sha256_bytes": byte_hash,
        "bytehash_pin": str(pin) if pin.exists() else None,
        "baseline_release_yield": freeze.get("baseline_release_yield"),
        "quality_rejections": freeze.get("quality_rejections"),
        "frozen_at": freeze.get("frozen_at"),
        "chain_to_b1": (freeze.get("chain_to_b1_freeze") or {})
        .get("b1_content_sha256"),
    }


def load_independent_baseline(
        path: Path = FREEZE_PATH) -> Dict[str, Any]:
    path = Path(path)
    integrity = verify_independent_baseline(path)
    if integrity.get("verdict") != "INTEGRITY_OK":
        raise RuntimeError(
            f"independent baseline integrity failure: {integrity} — "
            f"refusing to use a mutated freeze as the reference point")
    return json.loads(path.read_text(encoding="utf-8"))

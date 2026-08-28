"""Coder 2 Phase 2, B1 — FREEZE THE CURRENT BASELINE.

    CURRENT_BASELINE = 3/15 RELEASED, 12/15 QUALITY_REJECTED

This becomes the immutable reference point for measuring Coder 1's
repairs. The baseline file is written ONCE and never overwritten:

  * freeze_baseline() refuses to write over an existing baseline;
  * verify_baseline() re-derives the content hash and fails if the file
    was modified after freezing;
  * reaudit.py loads the baseline read-only and writes NEW timestamped
    measurement files instead of touching it;
  * the benchmark test suite pins the baseline hash so accidental
    modification fails CI (regression protection).

Recorded in the baseline: engine HEAD, threshold artifact hashes
(depth contract + dossier profile — any later change is THRESHOLD_DRIFT,
never silently absorbed), the split manifest hash, the seven-deficiency
measurement rows (CEO B6 baseline vocabulary), and the full tri-
measurement summary.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

BASELINE_DIR = Path(__file__).resolve().parents[2] / \
    "artifacts" / "benchmark" / "baseline"
BASELINE_PATH = BASELINE_DIR / "CURRENT_BASELINE.json"


def sha256_file(path: Path) -> Optional[str]:
    try:
        return hashlib.sha256(
            Path(path).read_bytes()).hexdigest()
    except Exception:
        return None


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def freeze_baseline(measurement: Dict[str, Any],
                    out_path: Path = BASELINE_PATH) -> Dict[str, Any]:
    """Write the baseline ONCE. Refuses to overwrite an existing file."""
    out_path = Path(out_path)
    if out_path.exists():
        existing = verify_baseline(out_path)
        return {
            "action": "REFUSED",
            "reason": "baseline already exists — it is immutable and is "
                      "never overwritten (CEO Phase 2 B1)",
            "path": str(out_path),
            "existing_integrity": existing.get("verdict"),
        }
    baseline = {
        "artifact": "CODER2_CURRENT_BASELINE",
        "owner": "CODER2",
        "frozen_at": measurement.get("measured_at"),
        "engine_head": measurement.get("engine_head"),
        "threshold_integrity": measurement.get("threshold_integrity"),
        "split_manifest_sha256": measurement.get("split_manifest_sha256"),
        "baseline_summary": measurement.get("baseline_summary"),
        "seven_deficiencies": measurement.get("seven_deficiencies"),
        "tri_measurement": measurement.get("tri_measurement"),
        "content_sha256": None,  # filled below
    }
    baseline["content_sha256"] = sha256_obj(
        {k: v for k, v in baseline.items() if k != "content_sha256"})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(baseline, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    return {"action": "FROZEN", "path": str(out_path),
            "content_sha256": baseline["content_sha256"]}


def verify_baseline(path: Path = BASELINE_PATH) -> Dict[str, Any]:
    """Integrity check: the baseline file must hash to its recorded
    content hash. Any modification after freezing is BASELINE_MUTATED."""
    path = Path(path)
    if not path.exists():
        return {"available": False, "verdict": "MISSING",
                "reason": f"no baseline at {path}"}
    try:
        baseline = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"available": False, "verdict": "BASELINE_MUTATED",
                "reason": f"unparseable baseline: {exc}"}
    recorded = baseline.get("content_sha256")
    if not recorded:
        return {"available": True, "verdict": "BASELINE_MUTATED",
                "reason": "baseline carries no content hash"}
    actual = sha256_obj(
        {k: v for k, v in baseline.items() if k != "content_sha256"})
    if actual != recorded:
        return {"available": True, "verdict": "BASELINE_MUTATED",
                "reason": f"content hash mismatch: recorded {recorded[:12]} "
                          f"!= actual {actual[:12]} — the baseline was "
                          f"modified after freezing"}
    return {"available": True, "verdict": "INTEGRITY_OK",
            "content_sha256": actual,
            "baseline_summary": baseline.get("baseline_summary"),
            "frozen_at": baseline.get("frozen_at"),
            "engine_head": baseline.get("engine_head")}


def load_baseline(path: Path = BASELINE_PATH) -> Dict[str, Any]:
    path = Path(path)
    integrity = verify_baseline(path)
    if integrity.get("verdict") != "INTEGRITY_OK":
        raise RuntimeError(
            f"baseline integrity failure: {integrity} — refusing to use a "
            f"mutated baseline as the reference point")
    return json.loads(path.read_text(encoding="utf-8"))

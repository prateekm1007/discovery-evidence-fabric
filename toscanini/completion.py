"""toscanini/completion.py — R446-C1 Task 4: the canonical completion
authority for the product boundary.

R445-C established run_manifest.json as the TRUE completion marker
(final_state.json is persisted PRE-evolution — a killed process between
the two writes leaves the run dir LOOKING complete while the evolution
loop never re-engaged; measured live on the R445 evolution re-runs).

This module makes that truth a derived, reusable authority:

  completion_marker_state(run_dir) ->
      {completion: COMPLETE_MARKED | NOT_MARKED, ...}

  COMPLETE_MARKED requires run_manifest.json to exist AND carry:
    - finished_at (non-null)   — the run() tail actually executed
    - final_status (non-null)  — the terminal verdict was recorded
    - failed_stages (dict)     — the honest failure ledger is present
    - final_envelope_hash      — the envelope identity closed

  Everything else — final_state.json alone, a package ZIP, a CIO with
  present=true, a GLB, a render record — is evidence about ARTIFACTS,
  never evidence that the run COMPLETED (Art. XXV: absence of the
  marker is not a negative verdict; Art. LXI: an incomplete run is an
  infrastructure state, never a scientific one).

The consumer contract (the directive's acceptance): no session may
become user-visible COMPLETE until this marker proves the relevant
stages actually completed. The worker's phase 4, the benchmark session
seeding, and the state-integrity battery all consume THIS function —
one authority (Art. X).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

MARKER_NAME = "run_manifest.json"
COMPLETE_MARKED = "COMPLETE_MARKED"
NOT_MARKED = "NOT_MARKED"

_REQUIRED_MARKER_FIELDS = ("finished_at", "final_status",
                           "failed_stages", "final_envelope_hash")


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001 — corrupt marker = NOT marked
        return None
    return None


def completion_marker_state(run_dir: Optional[Path]
                            ) -> Dict[str, Any]:
    """Derive the completion state from the run dir's OWN persisted
    marker. Never guesses, never promotes partial artifacts (Art. XXV)."""
    out: Dict[str, Any] = {
        "authority": MARKER_NAME,
        "completion": NOT_MARKED,
        "missing_marker_fields": [],
        "final_status": None,
        "failed_stages": None,
        "finished_at": None,
    }
    if run_dir is None:
        out["reason"] = "no run_dir recorded for this session"
        return out
    rd = Path(run_dir)
    if not rd.exists():
        out["reason"] = f"run_dir does not exist: {rd}"
        return out
    marker = _read_json(rd / MARKER_NAME)
    if marker is None:
        out["reason"] = (
            f"{MARKER_NAME} absent or unreadable — final_state.json and "
            "any package/geometry artifacts are NOT completion evidence; "
            "the run is incomplete (recoverable, never a verdict)")
        return out
    missing = [f for f in _REQUIRED_MARKER_FIELDS
               if marker.get(f) is None]
    out["final_status"] = marker.get("final_status")
    out["failed_stages"] = marker.get("failed_stages")
    out["finished_at"] = marker.get("finished_at")
    if missing:
        out["completion"] = NOT_MARKED
        out["missing_marker_fields"] = missing
        out["reason"] = (
            f"{MARKER_NAME} exists but lacks: {', '.join(missing)} — "
            "the run() tail did not complete; explicitly incomplete")
        return out
    out["completion"] = COMPLETE_MARKED
    out["reason"] = (
        f"{MARKER_NAME} proves completion: finished_at present, "
        f"final_status={marker.get('final_status')!r}, failed_stages "
        "ledger recorded, envelope hash closed")
    return out


def completion_proves_run(run_dir: Optional[Path]) -> bool:
    """The boolean form consumers gate on."""
    return completion_marker_state(run_dir)["completion"] == COMPLETE_MARKED

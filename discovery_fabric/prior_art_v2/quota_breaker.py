"""discovery_fabric/prior_art_v2/quota_breaker.py — R399 W2.4: the
patent-connector quota circuit breaker.

Directive: "PATENT CONNECTOR QUOTA EXHAUSTION: Implement a circuit
breaker. When Lens or another provider reports quota exhaustion such as
429: SOURCE_STATE = QUOTA_EXHAUSTED. Park the source for the relevant
quota window. Do not repeat futile queries."

Measured basis (R399 audit W2.3): with the Lens monthly quota spent,
every run still attempted 5 ladder queries x the patent sources, all
failing 429 — plus the per-grid-candidate collision re-runs
(4+ candidates x 5 steps) — pure latency (the 2s/5s backoff alone burns
~7.4 s per doomed query) and quota noise. The breaker parks the source
after the FIRST quota-class 429 so later queries are refused locally.

Distinction (never conflated):
  - 429 + quota signature (budget/quota/resets/exceeded/monthly) ->
    QUOTA_EXHAUSTED, parked for the quota window: until the provider's
    stated reset date when parseable, else a bounded 24 h window with
    one re-attempt per window (never a permanent silent disable).
  - plain 429 (short-window rate limit; measured to clear within
    seconds) -> NOT tripped here; the existing 2s/5s backoff in
    search_patents handles it.

Epistemic contract (Art. XXI.3 / XXV): a breaker refusal is recorded as
NOT_QUERIED_QUOTA_EXHAUSTED in the search error list — a provider state,
NEVER 'no results' and never absence. The state file is runtime state
(sibling of patentbear_meter.json); hermetic tests redirect it via the
QUOTA_BREAKER_PATH env (the conftest guard class).
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

# R482 (external audit P2 portability): the Windows
# collection class — conftest imports this module at
# collection time, so the lock goes through the shim.
from ..portable_flock import LOCK_EX, LOCK_UN, flock

REPO_ROOT = Path(__file__).resolve().parents[2]
BREAKER_PATH = Path(
    os.environ.get("QUOTA_BREAKER_PATH")
    or REPO_ROOT / "patent_sources" / "quota_breaker.json")

BREAKER_VERSION = "quota_breaker/1.0.0"

# A 429 whose body carries any of these is a QUOTA-CLASS refusal (the
# Lens monthly-budget message: "Insufficient budget ... Resets ...").
# A bare 429 (short rate-limit window) deliberately does NOT match.
_QUOTA_SIGNATURE = re.compile(
    r"insufficient\s+budget|quota|monthly|resets?\s|plan\s+limit|"
    r"exceeded.{0,40}(?:budget|limit|quota)", re.IGNORECASE)

# Fallback window when the provider states no reset date: 24 h, so a
# tripped source costs at most ONE wasted query per day until the quota
# genuinely resets (never a permanent disable — Art. XXV).
DEFAULT_WINDOW_S = 24 * 3600


def _now() -> float:
    return time.time()


def _read() -> Dict[str, Any]:
    try:
        return json.loads(BREAKER_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — absent/corrupt = no state
        return {"schema": 1, "sources": {}}


def _write(doc: Dict[str, Any]) -> None:
    BREAKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock = BREAKER_PATH.with_suffix(".lock")
    with open(lock, "w") as lf:
        flock(lf, LOCK_EX)
        try:
            BREAKER_PATH.write_text(json.dumps(doc, indent=1,
                                               sort_keys=True), encoding="utf-8")
        finally:
            flock(lf, LOCK_UN)


def is_quota_exhaustion(error_text: str) -> bool:
    """A quota-class 429 (vs a transient rate-limit 429)."""
    t = str(error_text or "")
    return "429" in t and bool(_QUOTA_SIGNATURE.search(t))


def _parse_reset(error_text: str) -> Optional[float]:
    """Best-effort parse of the provider's stated reset timestamp/date
    (e.g. 'Resets 2026-10-01T00:00:00Z' / 'Resets 2026-10-01')."""
    m = re.search(r"resets?\s+(\d{4}-\d{2}-\d{2}"
                  r"(?:[T ]\d{2}:\d{2}(?::\d{2})?Z?)?)",
                  str(error_text or ""), re.IGNORECASE)
    if not m:
        return None
    stamp = m.group(1).replace(" ", "T")
    if not stamp.endswith("Z") and "T" in stamp and len(stamp) == 16:
        stamp += ":00"
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            import datetime as _dt
            dt = _dt.datetime.strptime(stamp, fmt)
            return dt.replace(tzinfo=_dt.timezone.utc).timestamp() + 3600.0
        except ValueError:
            continue
    return None


def trip(source_id: str, error_text: str) -> Optional[Dict[str, Any]]:
    """Trip the breaker for a source on a quota-class 429. Returns the
    recorded state (None when the error is not quota-class — the caller
    then keeps its normal backoff path)."""
    if not is_quota_exhaustion(error_text):
        return None
    until = _parse_reset(error_text) or (_now() + DEFAULT_WINDOW_S)
    doc = _read()
    doc["schema"] = doc.get("schema", 1)
    doc.setdefault("sources", {})
    entry = {
        "source_state": "QUOTA_EXHAUSTED",
        "tripped_at": _now(),
        "tripped_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "until_epoch": until,
        "until_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                   time.gmtime(until)),
        "reason": str(error_text)[:300],
        "breaker_version": BREAKER_VERSION,
    }
    doc["sources"][source_id] = entry
    _write(doc)
    return entry


def check(source_id: str) -> Optional[Dict[str, Any]]:
    """The breaker state for a source, or None when the source is OK to
    query (no trip, or the window has passed — the expired entry is
    cleared so the next query re-attempts the source exactly once per
    window; a breaker is a parking function, never a kill)."""
    doc = _read()
    entry = (doc.get("sources") or {}).get(source_id)
    if not isinstance(entry, dict):
        return None
    if _now() >= float(entry.get("until_epoch") or 0):
        # window passed: clear + report clearable (one re-attempt)
        doc["sources"].pop(source_id, None)
        doc.setdefault("cleared", []).append({
            "source_id": source_id,
            "cleared_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime()),
            "window_expired": True})
        _write(doc)
        return None
    return entry


def refusal_record(source_id: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    """The honest search-error record for a breaker refusal (the shape
    search_patents appends per query+source)."""
    return {
        "source": source_id,
        "error": (f"quota breaker: {entry.get('source_state')} until "
                  f"{entry.get('until_utc')} — parked for the quota "
                  f"window ({entry.get('reason', '')[:120]}); NOT "
                  f"attempted, NOT absence (R399 W2.4 / Art. XXI.3)"),
        "epistemic_state": "NOT_QUERIED_QUOTA_EXHAUSTED",
        "source_state": "QUOTA_EXHAUSTED",
        "parked_until_utc": entry.get("until_utc"),
    }
